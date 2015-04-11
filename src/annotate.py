#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  annotate_segment.py
#  wide-language-index
#

from datetime import date
from os import path
import cmd
import collections
import glob
import heapq
import json
import random
import subprocess
import sys

import click
import pydub

import audio
import ui

SETS = {
    'global-top-20': set([
        'cmn', 'spa', 'eng', 'hin', 'arb', 'por', 'ben', 'rus', 'jpn', 'jav',
        'deu', 'wuu', 'kor', 'fra', 'tel', 'mar', 'tur', 'tam', 'vie', 'urd',
    ]),
    'global-top-40': set([
        'cmn', 'spa', 'eng', 'hin', 'arb', 'por', 'ben', 'rus', 'jpn', 'jav',
        'deu', 'wuu', 'kor', 'fra', 'tel', 'mar', 'tur', 'tam', 'vie', 'urd',
        'ita', 'pnb', 'yue', 'arz', 'pes', 'guj', 'nan', 'cjy', 'bho', 'pol',
        'kan', 'ukr', 'hsn', 'sun', 'mai', 'mal', 'ory', 'hak', 'pan', 'arq',
    ]),
    'region-top-5': set([
        'arz', 'arq', 'hau', 'amh', 'ary', 'hat', 'hrx', 'gug', 'lou', 'jam',
        'cmn', 'hin', 'arb', 'ben', 'jpn', 'spa', 'eng', 'por', 'rus', 'deu',
        'smo', 'fij', 'ton', 'mri', 'med',
    ]),
}

Segment = collections.namedtuple('Segment', 'sample offset duration')

GUIDELINE_VERSION = 2
GUIDELINES = """
ANNOTATION GUIDELINES v2

You are about to listen to a number of audio clips in different languages.
For each clip, we want to work out if it's suitable to use as a sample of
that language. Here's the guidelines:

noise?
        Mark with a "y" if the sample has loud noise interrupting it,
        someone talking over the back, or music playing.

wrong language?
        Mark with a "y" if you know that the sample is in the wrong language.
        For example, it might be all English, when the language is supposed to
        be Swahili. It is not expected that you can decide all these cases,
        leave it blank if unsure.

multiple languages?
        Mark with a "y" if you can tell that part of the clip is in a
        different language.

excess loan words?
        Mark with a "y" if many of the words are borrowed from English, making
        the sample not a good representation of the language. Use your own
        judgement here.

language or place reference?
        Samples that mention the name of their language or a distinctive place
        that the language is from may be inappropriate in the use of language
        guessing games. If an obvious reference is there, mark "y".

pauses?
        Are there long pauses which eat up much of the clip? If so, mark "y".

speakers
        Count the number of different people you hear speaking in the clip.
        Normally it will just be one or two.

genders
        Also keep track of each speaker's gender, if it's clear to you. If
        every speaker in the clip is male, pick "male". Likewise for female.
        Pick "mixed" if there's at least one speaker of each gender, and
        "unknown" if there's at least one speaker for which you can't tell.

You can exit the annotation at any time by pressing CTRL-C. You can also see
these instructions again by typing "help" at the menu.

Press "q" to continue.
"""


DEFAULT_DURATION_S = 20
SAMPLE_DIR = 'samples'
INDEX_DIR = 'index'


@click.command()
@click.option('--language-set',
              help='Only annotate a particular set of langauges.')
def main(language_set=None):
    """
    Begin an interactive annotation session, where you are played snippets of
    audio in different languages and you have to mark whether or not they are
    representative samples.
    """
    _validate_language_set(language_set)

    metadata = load_metadata(language_set=language_set)
    session = Session()

    ui.clear_screen()
    ui.pause('Beginning annotation, press ENTER to hear the first clip...')

    for segment in RandomSampler(metadata, DEFAULT_DURATION_S):
        ann, quit = annotate(segment, session.user, metadata)

        if ann is not None:
            save_annotation(segment.sample, ann, metadata)
            session.annotated += 1

        else:
            print('Skipping...')
            session.skipped += 1

        print()

        if quit:
            break

    session.summarize()


def _validate_language_set(language_set):
    if language_set is not None and language_set not in SETS:
        print('ERROR: language set "{0}" not one of: {1}'.format(
            language_set, ', '.join(sorted(SETS.keys()))
        ), file=sys.stderr)
        sys.exit(1)


class Session(object):
    "Statistics for an annotation session."
    def __init__(self):
        self.annotated = 0
        self.skipped = 0
        self.user = User.identify()

    def summarize(self):
        print('listened: {0}'.format(self.annotated + self.skipped))
        print('annotated: {0}'.format(self.annotated))
        print('skipped: {0}'.format(self.skipped))


class User(object):
    """
    Keep track of a user's name, email address and the last version of the
    annotation guidelines that they've seen.
    """
    def __init__(self, name, email, seen_guidelines=None):
        self.name = name
        self.email = email
        self.seen_guidelines = seen_guidelines

    @classmethod
    def load_default(cls):
        p = cls.settings_path()
        if path.exists(p):
            with open(p) as istream:
                return cls(**json.load(istream))

    @staticmethod
    def settings_path():
        return path.expanduser('~/.widelanguageindex')

    def save(self):
        with open(self.settings_path(), 'w') as ostream:
            json.dump({'name': self.name,
                       'email': self.email,
                       'seen_guidelines': self.seen_guidelines}, ostream)

    def __str__(self):
        return '{0} <{1}>'.format(self.name, self.email)

    @classmethod
    def identify(cls):
        user = cls.load_default()
        if user is None:
            user = cls.identify_interactive()

        if user.seen_guidelines is None:
            user.show_guidelines(
                'Please read the guidelines below before you start.'
            )
        elif user.seen_guidelines != GUIDELINE_VERSION:
            user.show_guidelines(
                'The annotation guidelines have changed, please read the '
                'new guidelines \nbefore continuing.'
            )

        return user

    def show_guidelines(self, message):
        print(message)
        ui.pause()
        page(GUIDELINES)
        self.seen_guidelines = GUIDELINE_VERSION
        self.save()

    @classmethod
    def identify_interactive(cls):
        print()
        print(
            "This is your first time annotating. We ask for your name and\n"
            "email in order to contact you about any of your annotations.\n"
        )
        name = ui.input_string('name')
        email = ui.input_email()
        return cls(name, email)


def load_metadata(language_set=None):
    # we might be looking at only a subset of languages
    if language_set is None:
        include_language = lambda l: True
    else:
        include_language = SETS[language_set].__contains__

    metadata = collections.defaultdict(dict)
    for f in glob.glob('index/*/*.json'):
        with open(f) as istream:
            rec = json.load(istream)
            lang = rec['language']
            if include_language(lang):
                checksum = rec['checksum']
                metadata[lang][checksum] = rec

    return metadata


class RandomSampler(object):
    """
    Provides an ordering over unannotated segments which prefers: languages
    with fewer samples, samples with fewer annotations, and segments which
    haven't been annotated before.
    """
    def __init__(self, metadata, duration):
        self.metadata = metadata
        self.duration = duration
        self.queue = self.build_queue()

    def build_queue(self):
        queue = [
            (lang_annotation_count(l, self.metadata),
             random.random(),  # don't sort by name
             l)
            for l in self.metadata.keys()
        ]
        heapq.heapify(queue)
        return queue

    def pop(self):
        _, _, l = heapq.heappop(self.queue)
        return l

    def push(self, l):
        heapq.heappush(self.queue, self.gen_key(l))

    def gen_key(self, l):
        return (lang_annotation_count(l, self.metadata),
                random.random(),  # randomly break ties
                l)

    def __iter__(self):
        while True:
            l = self.pop()
            yield self.find_segment(l)
            self.push(l)

    def find_segment(self, l):
        for sample in self.iter_samples(l):
            for segment in self.iter_segments(sample):
                return segment

    def iter_samples(self, l):
        "Favour samples with fewer annotations."
        samples = self.metadata[l]

        s_by_annotations = [
            (sample_annotation_count(s),
             sample_annotation_count(s, include_all=True),
             random.random(),
             s)
            for s in samples.values()
        ]
        s_by_annotations.sort()

        for _, _, _, s in s_by_annotations:
            yield s

    def iter_segments(self, sample):
        "Pick random segments that haven't been annotated yet."
        sample_len = sample_duration(sample)

        n_segments = int(sample_len / self.duration)
        segment_ids = list(range(n_segments))
        random.shuffle(segment_ids)

        seen = set([a['offset']
                    for a in sample.get('annotations', ())
                    if int(a['duration']) == self.duration])

        for segment_id in segment_ids:
            offset = segment_id * self.duration

            # skip if annotated already
            if offset in seen:
                continue

            yield Segment(sample, offset, self.duration)


def sample_duration(sample):
    filename = sample_filename(sample)
    audio = pydub.AudioSegment.from_mp3(filename)
    return audio.duration_seconds


def iter_segments(sample, segment_duration):
    sample_len = sample_duration(sample)

    # generate options
    unannotated = set()
    offset = 0
    while offset + segment_duration < sample_len:
        unannotated.add((offset, segment_duration))
        offset += segment_duration

    # eliminate annotated segments
    for annotation in sample.get('annotations', ()):
        offset = int(annotation['offset'])
        duration = int(annotation['duration'])
        unannotated.remove((offset, duration))

    unannotated = list(unannotated)
    random.shuffle(unannotated)

    for offset, duration in unannotated:
        yield Segment(sample, offset, duration)


def sample_filename(sample):
    return '{sample_dir}/{language}/{language}-{checksum}.mp3'.format(
        sample_dir=SAMPLE_DIR,
        language=sample['language'],
        checksum=sample['checksum'],
    )


def save_annotation(sample, annotation, metadata):
    lang = sample['language']
    c_before = lang_annotation_count(lang, metadata)

    # add this annotation
    sample.setdefault('annotations', []).append(annotation)

    metadata_file = metadata_filename(sample)
    s_norm = json.dumps(sample, indent=2, sort_keys=True)
    with open(metadata_file, 'w') as ostream:
        ostream.write(s_norm)

    # give a status update for this language
    c_after = lang_annotation_count(lang, metadata)

    print('{0}: {1} -> {2}'.format(lang, c_before, c_after))


def lang_annotation_count(language, metadata):
    return sum(
        sample_annotation_count(s)
        for s in metadata[language].values()
    )


def sample_annotation_count(sample, include_all=False):
    if include_all:
        return len(sample.get('annotations', ()))

    return sum(a['label'] == 'good'
               for a in sample.get('annotations', ()))


def metadata_filename(sample):
    return '{index_dir}/{language}/{language}-{checksum}.json'.format(
        index_dir=INDEX_DIR,
        language=sample['language'],
        checksum=sample['checksum'],
    )


def annotate(segment, user, metadata):
    c = AnnotateCmd(segment, user, metadata)
    c.cmdloop()
    return c.annotation, c.quit_flag


class AnnotateCmd(cmd.Cmd):
    def __init__(self, segment, user, metadata):
        super(AnnotateCmd, self).__init__()
        self.segment = segment
        self.user = user
        self.annotation = None
        self.quit_flag = False
        self.language_names = load_language_names()
        self.metadata = metadata

        listened = self._play()
        if listened:
            self._edit()

    def _play(self):
        s = self.segment
        filename = sample_filename(s.sample)
        basename = path.basename(filename)
        print('{0} ({1} at {2} -> {3})'.format(
            self.language_names[s.sample['language']],
            basename,
            s.offset,
            s.offset + s.duration,
        ))

        with audio.cropped(filename, s.offset, s.duration) as clip:
            return audio.play_mp3(clip)

    def _edit(self):
        try:
            ok = ui.input_bool('Is the sample ok')
            if not ok:
                problems = ui.input_multi_options(
                    'Problems with the sample',
                    ['noise', 'wrong language',
                     'multiple languages', 'excess loan words',
                     'language or place reference', 'pauses'],
                )
            else:
                problems = []

            speakers = ui.input_number('speakers', minimum=0, maximum=10)
            if speakers > 0:
                genders = ui.input_single_option(
                    'Gender of speakers',
                    ['male', 'female', 'mixed', 'unclear'],
                )
            else:
                genders = 'unclear'

            self.annotation = {
                'problems': sorted(problems),
                'speakers': speakers,
                'genders': genders,
                'label': 'good' if ok else 'bad',
                'date': str(date.today()),
                'offset': self.segment.offset,
                'duration': self.segment.duration,
                'annotator': str(self.user)
            }

        except KeyboardInterrupt:
            pass

    def do_play(self, line):
        self._play()

    def help_play(self):
        print('Play the sample again')

    def do_p(self, line):
        return self.do_play(line)

    def do_edit(self, line):
        try:
            self._edit()
        except KeyboardInterrupt:
            pass

    def help_edit(self):
        print('Redo the annotation for this sample')

    def do_e(self, line):
        return self.do_edit(line)

    def do_next(self, line):
        return True

    def help_next(self, line):
        print('Continue to the next sample')

    def do_n(self, line):
        return self.do_next(line)

    def do_quit(self, line):
        self.quit_flag = True
        return True

    def help_quit(self):
        print('Quit and save the current annotation')

    def do_q(self, line):
        return self.do_quit(line)

    def do_abort(self, line):
        self.annotation = None
        return self.do_quit(line)

    def help_abort(self):
        print('Quit without saving the current example')

    def do_a(self, line):
        return self.do_abort(line)

    def do_view(self, line):
        print(json.dumps(self.annotation, indent=2, sort_keys=True))

    def do_v(self, line):
        return self.do_view(line)

    def do_guidelines(self, line):
        page(GUIDELINES)

    def do_stats(self, line):
        per_lang = collections.Counter(
            {lang: lang_annotation_count(lang, self.metadata)
             for lang in self.metadata.keys()}
        )

        content = '\n'.join('{0} {1}'.format(l, c)
                            for (l, c) in per_lang.most_common())
        page(content)

    def do_s(self, line):
        return self.do_stats(line)


def page(content):
    "Print the string through less."
    try:
        # args stolen fron git source, see `man less`
        pager = subprocess.Popen(['less', '-F', '-R', '-S', '-X', '-K'],
                                 stdin=subprocess.PIPE,
                                 stdout=sys.stdout)
        pager.stdin.write(content.encode('utf8'))
        pager.stdin.close()
        pager.wait()
    except KeyboardInterrupt:
        # let less handle this, -K will exit cleanly
        pass


def load_language_names():
    name_index = json.load(open('ext/name_index_20140320.json'))
    return {r['id']: r['print_name']
            for r in name_index}


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # exit silently without complaint
        pass
