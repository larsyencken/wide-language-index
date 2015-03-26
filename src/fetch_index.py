#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  fetch_index.py
#  wide-langauge-index
#

"""
Download the actual sample files for the language game index.
"""

from __future__ import absolute_import, print_function, division

from os import path
import glob
import hashlib
import json
import os

import requests
import click


INDEX_DIR = path.normpath(path.join(path.dirname(__file__),
                                    '..', 'index'))
SAMPLE_DIR = path.normpath(path.join(path.dirname(__file__),
                                     '..', 'samples'))


@click.command()
@click.option('--index-dir', default=INDEX_DIR,
              help='Use a different index folder.')
@click.option('--output-dir', default=SAMPLE_DIR,
              help='Use a different output folder.')
@click.option('--language', help='Only fetch the given language.')
def fetch_index(index_dir=INDEX_DIR, output_dir=SAMPLE_DIR, language=None):
    """
    Fetch a copy of every sample in the index, placing them in output_dir.
    """
    n_errors = 0
    record_files = get_record_files(index_dir, language=language)
    for i, f in enumerate(record_files):
        rec = json.load(open(f))
        lang = rec['language']
        checksum = rec['checksum']

        # e.g. samples/fra/fra-8da6ee6728fa1f38c99e16585752ccaa.mp3
        dest_file = os.path.join(output_dir, lang,
                                 '{0}-{1}.mp3'.format(lang, checksum))
        print('[{0}/{1}] {2}/{2}-{3}.mp3'.format(
            i + 1,
            len(record_files),
            lang,
            checksum
        ))

        for media_url in rec['media_urls']:
            try:
                download_and_validate(media_url, checksum, dest_file)
                break
            except DownloadError as e:
                pass
        else:
            print('ERROR: {0} -- skipping'.format(e.args[0]))
            n_errors += 1

    print('\n{0} records, {1} errors'.format(len(record_files),
                                             n_errors))


def get_record_files(index_dir, language=None):
    if language is None:
        pattern = '{0}/*/*.json'.format(index_dir)
    else:
        pattern = '{0}/{1}/*.json'.format(index_dir, language)

    return sorted(glob.glob(pattern))


class DownloadError(Exception):
    pass


def download_and_validate(url, checksum, dest_file):
    if not os.path.exists(dest_file):
        resp = requests.get(url)
        if resp.status_code != 200:
            raise DownloadError('got HTTP {0} downloading {1}'.format(
                resp.status_code,
                url,
            ))
        data = resp.content
    else:
        # already downloaded
        data = open(dest_file, 'rb').read()

    c = hashlib.md5(data).hexdigest()
    if c != checksum:
        raise DownloadError(
            'checksum mismatch downloading {0} -- got {1}'.format(
                url,
                c,
            )
        )

    parent_dir = os.path.dirname(dest_file)
    if not os.path.isdir(parent_dir):
        os.mkdir(parent_dir)

    with open(dest_file, 'wb') as ostream:
        ostream.write(data)


if __name__ == '__main__':
    fetch_index()
