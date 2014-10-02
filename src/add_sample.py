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
import optparse
import hashlib
import tempfile
import json
import subprocess as sp

import sh


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


def add_sample(language, source_url):
    sample = download_sample(source_url)
    checksum = checksum_sample(sample)
    file_sample(language, checksum, sample)
    filename = make_stub_record(language, checksum, source_url)
    return filename


def download_sample(source_url):
    if not source_url.endswith('.mp3'):
        print('ERROR: sample doesn\'t appear to be in mp3 format',
              file=sys.stderr)
        sys.exit(1)

    t = tempfile.NamedTemporaryFile(delete=False)
    sh.wget('-O', t.name, source_url, _out=open('/dev/stdout', 'wb'),
            _err=open('/dev/stderr', 'wb'))
    return t


def checksum_sample(sample):
    with open(sample.name, 'rb') as istream:
        return hashlib.md5(istream.read()).hexdigest()


def file_sample(language, checksum, sample):
    sample_name = '{language}-{checksum}.mp3'.format(language=language,
                                                     checksum=checksum)
    parent_dir = path.join(SAMPLE_DIR, language)
    if not path.isdir(parent_dir):
        os.mkdir(parent_dir)

    dest_file = path.join(parent_dir, sample_name)
    sh.mv(sample.name, dest_file)


def make_stub_record(language, checksum, url):
    parent_dir = path.join(INDEX_DIR, language)
    if not path.isdir(parent_dir):
        os.mkdir(parent_dir)

    record_file = path.join(parent_dir,
                            '{language}-{checksum}.json'.format(**locals()))
    print(record_file)

    record = TEMPLATE.copy()
    record['language'] = language
    record['checksum'] = checksum
    record['media_urls'] = [url]

    with open(record_file, 'w') as ostream:
        json.dump(record, ostream, indent=2, sort_keys=True)

    return record_file


def open_in_editor(filename):
    editor = os.environ.get('EDITOR', 'vim')
    p = sp.Popen([editor, filename])
    p.wait()


def _create_option_parser():
    usage = \
"""%prog [options] <language_code> <source_url>

Make a stub record for the given audio sample."""  # nopep8

    parser = optparse.OptionParser(usage)
    parser.add_option('--edit', action='store_true',
                      help='Open the new record in your default editor.')

    return parser


def main(argv):
    parser = _create_option_parser()
    (options, args) = parser.parse_args(argv)

    if len(args) != 2:
        parser.print_help()
        sys.exit(1)

    filename = add_sample(*args)
    if options.edit:
        open_in_editor(filename)


if __name__ == '__main__':
    main(sys.argv[1:])
