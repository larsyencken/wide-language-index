#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  annotate_segment.py
#  wide-language-index
#

from os import path
import json
import glob
from collections import defaultdict, namedtuple
import random
import cmd
import copy
from datetime import date

import pydub

import play_offset
import ui

Segment = namedtuple('Segment', 'sample offset duration')


DEFAULT_DURATION_S = 20
SAMPLE_DIR = 'samples'
INDEX_DIR = 'index'


class User(object):
    def __init__(self, name, email):
        self.name = name
        self.email = email

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
                       'email': self.email}, ostream)

    def __str__(self):
        return '{0} <{1}>'.format(self.name, self.email)


def identify_user():
    user = User.load_default()
    if user is not None:
        return user

    user = identify_user_interactive()
    if user.save:
        user.save()


def load_metadata():
    metadata = defaultdict(dict)
    for f in glob.glob('index/*/*.json'):
        with open(f) as istream:
            rec = json.load(istream)
            lang = rec['language']
            checksum = rec['checksum']
            metadata[lang][checksum] = rec

    return metadata


def random_sample(metadata, duration):
    languages = list(metadata.keys())
    random.shuffle(languages)
    languages.sort(key=lambda l: annotation_count(metadata[l]))

    for sample in iter_samples(languages, metadata):
        for segment in iter_segments(sample, duration):
            return segment


def iter_samples(languages, metadata):
    """
    Go through unlabelled samples in order. Firstly order by language, by
    number of annotations ascending. Then prefer samples which haven't been
    annotated yet.
    """
    # order languages by number of annotations, least to most
    l_by_annotations = [(num_lang_annotations(metadata[l]), l)
                        for l in languages]
    l_by_annotations.sort(key=lambda kv: kv[0])

    for _, l in l_by_annotations:
        samples = metadata[l]
        s_by_annotations = [(num_sample_annotations(s), s)
                            for s in samples.values()]
        s_by_annotations.sort(key=lambda kv: kv[0])
        for _, s in s_by_annotations:
            yield s


def num_lang_annotations(l):
    "Count the number of good annotations for a language."
    return sum(num_sample_annotations(s)
               for s in l.values())


def num_sample_annotations(s):
    return sum(1 for a in s.get('annotations', ())
               if a['label'] == 'good')


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


def annotation_count(lang_records):
    empty = []
    return sum(len(r.get('annotations', empty))
               for r in lang_records.values())


def identify_user_interactive():
    import npyscreen as nps

    class UserApp(nps.NPSApp):
        def main(self):
            f = nps.Form(name='Annotator details')
            self.name = f.add(nps.TitleText, name='Name: ')
            self.email = f.add(nps.TitleText, name='Email: ')
            f.edit()

    app = UserApp()
    app.run()
    return User(app.name.value, app.email.value)


def sample_filename(sample):
    return '{sample_dir}/{language}/{language}-{checksum}.mp3'.format(
        sample_dir=SAMPLE_DIR,
        language=sample['language'],
        checksum=sample['checksum'],
    )


def update_metadata(sample, annotation):
    # add this annotation
    sample.setdefault('annotations', []).append(annotation)

    metadata_file = metadata_filename(sample)
    with open(metadata_file, 'w') as ostream:
        json.dump(sample, ostream, indent=2, sort_keys=True)


def metadata_filename(sample):
    return '{index_dir}/{language}/{language}-{checksum}.json'.format(
        index_dir=INDEX_DIR,
        language=sample['language'],
        checksum=sample['checksum'],
    )


def main():
    annotated = 0
    skipped = 0

    user = identify_user()
    metadata = load_metadata()

    while True:
        segment = random_sample(metadata, DEFAULT_DURATION_S)
        c = AnnotateCmd(segment)
        c.cmdloop()
        if c.annotation is not None:
            ann = copy.deepcopy(c.annotation)
            ann['annotation'] = str(user)
            update_metadata(segment.sample, c.annotation)
            annotated += 1
        else:
            print('Skipping...')
            skipped += 1

            if c.quit_flag:
                break

    print('listened: {0}'.format(annotated + skipped))
    print('annotated: {0}'.format(annotated))
    print('Skipped: {0}'.format(skipped))


class AnnotateCmd(cmd.Cmd):
    def __init__(self, segment):
        super(AnnotateCmd, self).__init__()
        self.segment = segment
        self.annotation = None
        self.quit_flag = False

        self._play()
        self._edit()

    def _play(self):
        s = self.segment
        filename = sample_filename(s.sample)
        basename = path.basename(filename)
        print('Playing {0} at ({1} -> {2})'.format(
            basename,
            s.offset,
            s.offset + s.duration,
        ))
        play_offset.play_offset(filename, s.offset, s.duration)

    def _edit(self):
        try:
            problems = ui.input_multi_options(
                'Problems with the sample',
                ['noise', 'multiple languages', 'excess loan words'],
            )
            speakers = ui.input_number('speakers', minimum=1, maximum=10)
            gender = ui.input_single_option(
                'Gender of speakers',
                ['male', 'female', 'mixed', 'unclear'],
            )

            self.annotation = {
                'problems': sorted(problems),
                'speakers': speakers,
                'gender': gender,
                'label': 'good' if not problems else 'bad',
                'date': str(date.today()),
                'offset': self.segment.offset,
                'duration': self.segment.duration,
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


if __name__ == '__main__':
    main()
