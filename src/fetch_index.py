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
import sys
import optparse
import hashlib
import glob
import json

import requests


def fetch_index(index_dir, output_dir):
    for f in glob.glob('{0}/*/*.json'.format(index_dir)):
        rec = json.load(open(f))
        url = rec['media_urls'][-1]

        lang = rec['language']
        checksum = rec['checksum']
        dest_file = os.path.join(output_dir, lang,
                                 '{0}-{1}.mp3'.format(lang, checksum))

        print(dest_file)
        download_and_validate(url, checksum, dest_file)


def download_and_validate(url, checksum, dest_file):
    if not os.path.exists(dest_file):
        resp = requests.get(url)
        if resp.status_code != 200:
            raise Exception('got HTTP {0} downloading {1}'.format(
                resp.status_code,
                url,
            ))
        data = resp.content

    else:
        # already downloaded
        data = open(dest_file).read()

    c = hashlib.md5(data).hexdigest()
    if c != checksum:
        raise ValueError(
            'checksum mismatch downloading {0} -- got {1}'.format(
                url,
                c,
            )
        )

    parent_dir = os.path.dirname(dest_file)
    if not os.path.isdir(parent_dir):
        os.mkdir(parent_dir)

    with open(dest_file, 'w') as ostream:
        ostream.write(data)


def _create_option_parser():
    usage = \
"""%prog [options] index_dir output_dir

Fetch a copy of every sample in the index, placing them in output_dir."""  # nopep8

    parser = optparse.OptionParser(usage)

    return parser


def main(argv):
    parser = _create_option_parser()
    (options, args) = parser.parse_args(argv)

    if len(args) != 2:
        parser.print_help()
        sys.exit(1)

    fetch_index(*args)


if __name__ == '__main__':
    main(sys.argv[1:])
