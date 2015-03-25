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

import os
import hashlib
import glob
import json

import requests
import click


@click.command()
@click.argument('index_dir')
@click.argument('output_dir')
@click.option('--language', help='Only fetch the given language.')
def fetch_index(index_dir, output_dir, language=None):
    """
    Fetch a copy of every sample in the index, placing them in output_dir.
    """
    record_files = get_record_files(index_dir, language=language)
    for i, f in enumerate(record_files):
        rec = json.load(open(f))
        lang = rec['language']
        checksum = rec['checksum']

        # e.g. samples/fra/fra-8da6ee6728fa1f38c99e16585752ccaa.mp3
        dest_file = os.path.join(output_dir, lang,
                                 '{0}-{1}.mp3'.format(lang, checksum))
        print('[{0}/{1}] {2}'.format(
            i + 1,
            len(record_files),
            dest_file
        ))

        for media_url in rec['media_urls']:
            try:
                download_and_validate(media_url, checksum, dest_file)
                break
            except DownloadError as e:
                pass
        else:
            print('ERROR: {0} -- skipping'.format(e.args[0]))


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
