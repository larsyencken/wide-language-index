#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  add_sample.py
#  wide-language-index
#

"""
Simplify adding a sample to the index.
"""

import os
from os import path
import sys
import hashlib
import tempfile
import json
import subprocess as sp
import shutil

import sh
import click

from audio import AudioSample
import youtube


BASE_DIR = path.abspath(path.join(path.dirname(__file__), '..'))
INDEX_DIR = path.join(BASE_DIR, 'index')
SAMPLE_DIR = path.join(BASE_DIR, 'samples')

TEMPLATE = {
    "checksum": "",
    "date": "",
    "language": "",
    "media_urls": [],
    "source_name": "",
    "source_url": ""
}


NO_METADATA = {}


@click.command()
@click.argument('language')
@click.argument('source_url')
@click.option('--edit', is_flag=True,
              help='Open the new record in an editor')
@click.option('--mirror', is_flag=True,
              help='Mirror the sample to S3')
def main(language: str, source_url: str, edit: bool=False, mirror: bool=False):
    """
    Add a single language example to the index.
    """
    filename = add_sample(language, source_url)

    if edit:
        open_in_editor(filename)


def add_sample(language: str, source_url: str) -> str:
    sample = fetch_sample(source_url)
    checksum = checksum_sample(sample)
    file_sample(language, checksum, sample)
    filename = make_stub_record(language, checksum, source_url, sample.metadata)
    return filename


def fetch_sample(source_url: str) -> AudioSample:
    "Ingest the sample to a local temporary file."
    if is_url(source_url):
        if youtube.is_youtube_url(source_url):
            sample = youtube.download_youtube_sample(source_url)
        else:
            sample = download_sample(source_url)
    else:
        sample = copy_sample(source_url)

    return sample


def copy_sample(source_file: str) -> AudioSample:
    t = tempfile.NamedTemporaryFile(delete=False)
    shutil.copy(source_file, t.name)
    return AudioSample(tempfile=t)


def is_url(source_url: str) -> bool:
    return source_url.startswith('http')


def download_sample(source_url: str) -> AudioSample:
    "Download an mp3 file from the internet."
    metadata = {'source_url': source_url}

    if not source_url.endswith('.mp3'):
        print('ERROR: sample doesn\'t appear to be in mp3 format',
              file=sys.stderr)
        sys.exit(1)

    t = tempfile.NamedTemporaryFile(delete=False)
    sh.wget('-O', t.name, source_url, _out=open('/dev/stdout', 'wb'),
            _err=open('/dev/stderr', 'wb'))

    return AudioSample(tempfile=t, metadata=metadata)


def checksum_sample(sample: AudioSample) -> str:
    with open(sample.filename, 'rb') as istream:
        return hashlib.md5(istream.read()).hexdigest()


def file_sample(language: str, checksum: str, sample: AudioSample) -> None:
    sample_name = '{language}-{checksum}.mp3'.format(language=language,
                                                     checksum=checksum)
    parent_dir = path.join(SAMPLE_DIR, language)
    if not path.isdir(parent_dir):
        os.mkdir(parent_dir)

    dest_file = path.join(parent_dir, sample_name)
    sh.mv(sample.filename, dest_file)


def make_stub_record(language: str, checksum: str, url: str,
                     metadata: dict) -> str:
    parent_dir = path.join(INDEX_DIR, language)
    if not path.isdir(parent_dir):
        os.mkdir(parent_dir)

    record_file = path.join(parent_dir,
                            '{language}-{checksum}.json'.format(**locals()))
    print(relative_path(record_file))

    record = TEMPLATE.copy()
    record['language'] = language
    record['checksum'] = checksum
    record['media_urls'] = [url]
    record['title'] = metadata.get('title', '')
    record['date'] = metadata.get('date', '')
    record['source_name'] = metadata.get('source_name', '')
    record['source_url'] = metadata.get('source_url', '')

    with open(record_file, 'w') as ostream:
        json.dump(record, ostream, indent=2, sort_keys=True)

    return record_file


def open_in_editor(filename: str) -> None:
    editor = os.environ.get('EDITOR', 'vim')
    p = sp.Popen([editor, filename])
    p.wait()


def relative_path(filename: str) -> str:
    "Attempt to convert the filename into just the path suffix from here."
    here = os.path.abspath('.')
    filename = os.path.abspath(filename)
    if filename.startswith(here):
        return filename[len(here):].lstrip('/')

    return filename


if __name__ == '__main__':
    main()
