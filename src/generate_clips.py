# -*- coding: utf-8 -*-
#
#  generate_clips.py
#  wide-language-index
#

import os
import glob
import json
import shutil

import click

import audio


@click.command()
def make_clips():
    """
    Generate the short clips for every good annotation in the dataset.
    """
    for sample, annotation in iter_annotations():
        make_clip(sample, annotation)


def iter_annotations():
    for filename in glob.glob('index/*/*.json'):
        with open(filename) as istream:
            sample = json.load(istream)
            for annotation in sample.get('annotations', []):
                if annotation['label'] == 'good':
                    yield sample, annotation


def make_clip(sample, annotation):
    source_file = 'samples/{language}/{language}-{checksum}.mp3'.format(
        language=sample['language'],
        checksum=sample['checksum'],
    )
    dest_file = ('samples/_annotated/{language}/{language}-'
                 '{checksum}-{offset}-{end}.mp3'.format(
                     language=sample['language'],
                     checksum=sample['checksum'],
                     offset=annotation['offset'],
                     end=annotation['offset'] + annotation['duration'],
                 ))
    print(dest_file)

    if os.path.exists(dest_file):
        return

    parent_dir = os.path.dirname(dest_file)
    if not os.path.isdir(parent_dir):
        os.mkdir(parent_dir)

    with audio.cropped(source_file, annotation['offset'],
                       annotation['duration']) as temp_file:
        shutil.copy(temp_file, dest_file)


if __name__ == '__main__':
    make_clips()
