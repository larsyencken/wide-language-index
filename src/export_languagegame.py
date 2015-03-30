# -*- coding: utf-8 -*-
#
#  export_languagegame.py
#  wide-language-index
#

"""
Export a snapshot of the index and accompanying audio for use in the Great
Language Game. A snapshot has two components:

export_dir/contents.csv
export_dir/media/{lang}/{lang}-{offset}-{duration}.mp3
...
"""

import collections
import glob
import json
import pathlib
import shutil

import click
import dateutil
import pandas as pd
import sh


DURATION_S = 20


@click.command()
@click.argument('dest_dir')
@click.option('--validate', is_flag=True,
              help='Validate an existing directory')
def main(dest_dir, validate=False):
    """
    Export a snapshot of the index and accompanying audio for use in the Great
    Lanugage Game.
    """
    dest_dir = pathlib.Path(dest_dir) / get_revision_name()
    dataset = load_dataset()
    save_contents(dataset, dest_dir)
    save_audio(dataset, dest_dir)


def get_revision_name():
    sha1 = sh.git('--no-pager', 'rev-parse',
                  'HEAD').stdout.strip().decode('utf8')
    date_s = sh.git('--no-pager', 'show', '-s', '--format=%ci',
                    'HEAD').stdout.strip()
    date = dateutil.parser.parse(date_s).date()
    return '{0}-{1}'.format(date, sha1[:8])


def load_dataset():
    rows = []
    for filename in glob.glob('index/*/*.json'):
        with open(filename) as istream:
            r = json.load(istream)

            for ann_record in iter_annotations(r):
                rows.append(ann_record)

    rows.sort(key=lambda r: (
        r['checksum'],
        r['offset']
    ))

    return rows


def iter_annotations(sample):
    # group annotations by offset
    by_offset = collections.defaultdict(list)
    for a in sample.get('annotations', ()):
        if a['duration'] != DURATION_S:
            continue

        offset = a['offset']
        by_offset[offset].append(a)

    for offset, annotations in sorted(by_offset.items(),
                                      key=lambda kv: kv[0]):
        # require all annotations to be good
        if all(a['label'] == 'good' for a in annotations):
            a = annotations[0]
            rec = {
                'checksum': sample['checksum'],
                'date': sample['date'],
                'duration': a['duration'],
                'genders': a['genders'],
                'language': sample['language'],
                'offset': a['offset'],
                'source_name': sample['source_name'],
                'source_url': sample['source_url'],
                'speakers': a['speakers'],
                'title': sample['title'],
            }
            rec['filename'] = annotation_filename(rec)
            yield rec


def save_contents(dataset, dest_dir):
    print('Saving contents...')
    df = pd.DataFrame.from_records(dataset)
    dest = pathlib.Path(dest_dir)
    if not dest.is_dir():
        dest.mkdir(parents=True)
    df.to_csv(str(dest / 'contents.csv'), index=False)


def save_audio(dataset, dest_dir):
    print('Copying audio...')
    base = pathlib.Path('samples/_annotated')
    dest = pathlib.Path(dest_dir)
    for ann in dataset:
        source_file = base / ann['filename']
        dest_file = dest / ann['filename']
        parent = dest_file.parent
        if not parent.is_dir():
            parent.mkdir(parents=True)

        shutil.copy(str(source_file), str(dest_file))


def annotation_filename(r):
    filename = '{0}/{0}-{1}-{2}-{3}.mp3'.format(
        r['language'],
        r['checksum'],
        r['offset'],
        r['offset'] + r['duration'],
    )
    return filename


def iter_index():
    for f in sorted(glob.glob('index/*/*.json')):
        with open(f) as istream:
            yield json.load(istream)


def make_parent_dir(dest_file):
    parent_dir = os.path.dirname(dest_file)
    sh.mkdir('-p', parent_dir)


if __name__ == '__main__':
    main()
