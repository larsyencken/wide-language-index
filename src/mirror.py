# -*- coding: utf-8 -*-
#
#  mirror.py
#  wide-language-index
#

from __future__ import absolute_import, print_function, division

from os import path
import glob
import hashlib
import json
import os
import sys

import boto
import click


BUCKET = 'mirror.widelanguageindex.org'


@click.command()
@click.option('--language',
              help='Only mirror the given language.')
def main(language=None):
    """
    Mirror samples to Amazon S3, in case the original publisher takes them
    down. Add the mirror URL as a secondary mirror in the index record.
    """
    s3 = boto.connect_s3()
    bucket = s3.get_bucket(BUCKET)

    print('Scanning records...')
    queue = []
    for record in iter_samples(language=language):
        if not sample_is_mirrored(record):
            queue.append(record)

    print('{0} samples to be mirrored'.format(len(queue)))
    for i, record in enumerate(queue):
        print('[{0}/{1}] '.format(i + 1, len(queue)), end='')
        mirror_sample(record, bucket)
        save_record(record)


def iter_samples(language=None):
    if language is not None:
        pattern = 'index/{0}/*.json'.format(language)
    else:
        pattern = 'index/*/*.json'

    for f in sorted(glob.glob(pattern)):
        with open(f) as istream:
            yield json.load(istream)


def sample_is_mirrored(record):
    return any(BUCKET in url for url in record['media_urls'])


def mirror_sample(record, bucket):
    name = '{language}/{language}-{checksum}.mp3'.format(**record)

    filename = 'samples/{0}'.format(name)
    if not path.exists(filename):
        bail('missing file {0}, did you run "make fetch"?'.format(filename))

    size = file_size(filename)
    print('{0} ({1})'.format(name, size))

    checksum = md5_checksum(filename)
    if checksum != record['checksum']:
        bail('invalid checksum for file {0}'.format(filename))

    key = bucket.new_key(name)

    # cache for 5 years
    headers = {'Cache-Control': 'max-age=%d, public' % (3600 * 24 * 360 * 5)}

    key.set_contents_from_filename(filename, headers=headers)

    key.set_acl('public-read')

    record['media_urls'].append(
        'http://mirror.widelanguageindex.org/{0}'.format(name)
    )


def save_record(record):
    filename = 'index/{language}/{language}-{checksum}.json'.format(**record)

    s = json.dumps(record, indent=2, sort_keys=True)
    with open(filename, 'w') as ostream:
        ostream.write(s)


def md5_checksum(filename):
    with open(filename, 'rb') as istream:
        return hashlib.md5(istream.read()).hexdigest()


def bail(message):
    print('ERROR: {0}'.format(message))
    sys.exit(1)


def file_size(filename):
    return '%.01fM' % (os.stat(filename).st_size / 2**20)


if __name__ == '__main__':
    main()
