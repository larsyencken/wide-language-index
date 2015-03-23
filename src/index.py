# -*- coding: utf-8 -*-
#
#  index.py
#  wide-language-index
#

"""
Tools for managing the index.
"""

from os import path
import glob
import hashlib
import json
import shutil
import tempfile

import sh
import jsonschema

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36'  # noqa
HERE = path.abspath(path.dirname(__file__))
INDEX_DIR = path.join(HERE, '../index')
SAMPLE_DIR = path.join(HERE, '../samples')


class DownloadError(Exception):
    pass


def stage_audio(url, language, user_agent=DEFAULT_USER_AGENT):
    "Fetch audio and stage it in the samples/ directory."
    with tempfile.NamedTemporaryFile(suffix='.mp3') as t:
        try:
            sh.wget('-e', 'robots=off', '-U', user_agent, '-O', t.name, url)
        except sh.ErrorReturnCode_8:
            raise DownloadError(url)

        checksum = md5_checksum(t.name)
        filename = path.join(
            SAMPLE_DIR,
            '{language}/{language}-{checksum}.mp3'.format(language=language,
                                                          checksum=checksum)
        )
        directory = path.dirname(filename)
        sh.mkdir('-p', directory)
        shutil.copy(t.name, filename)

        return filename, checksum


def scan():
    "Return a set of urls and checksums that have already been indexed."
    seen = set()
    for f in glob.glob(path.join(INDEX_DIR, '*/*.json')):
        with open(f) as istream:
            r = json.load(istream)
            mark_as_seen(r, seen)

    return seen


def mark_as_seen(sample, seen):
    seen.add(sample['source_url'])
    seen.add(sample['checksum'])
    seen.update(sample['media_urls'])


def md5_checksum(filename):
    with open(filename, 'rb') as istream:
        return hashlib.md5(istream.read()).hexdigest()


def load_schema():
    filename = path.join(INDEX_DIR, 'schema.json')
    with open(filename) as istream:
        return json.load(istream)


def save(sample, schema=None):
    schema = schema or load_schema()
    jsonschema.validate(sample, schema)
    filename = path.join(
        INDEX_DIR,
        '{language}/{language}-{checksum}.json'.format(**sample)
    )
    directory = path.dirname(filename)
    sh.mkdir('-p', directory)
    s = json.dumps(sample, indent=2, sort_keys=True)
    with open(filename, 'w') as ostream:
        ostream.write(s)
