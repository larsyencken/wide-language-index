# -*- coding: utf-8 -*-
#
#  index.py
#  wide-language-index
#

"""
Tools for managing the index.
"""

from collections import namedtuple, Counter
from contextlib import contextmanager
from os import path
from urllib.parse import urlparse
import glob
import hashlib
import json
import shutil
import tempfile

import jsonschema
import sh
import requests

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36"  # noqa
HERE = path.abspath(path.dirname(__file__))
INDEX_DIR = path.join(HERE, "../index")
SAMPLE_DIR = path.join(HERE, "../samples")

SUPPORTED_FORMATS = set(["mp3", "m4a"])


StagedFile = namedtuple("StagedFile", "filename checksum orig_checksum")


class DownloadError(Exception):
    pass


class CodecError(Exception):
    pass


def stage_audio(url, language, user_agent=DEFAULT_USER_AGENT, method="wget"):
    "Fetch audio and stage it in the samples/ directory."

    audio_type = _detect_audio_type(url)
    if audio_type not in SUPPORTED_FORMATS:
        raise CodecError(
            "{0} not a supported codec, from url {1}".format(audio_type, url)
        )

    with downloaded(url, "." + audio_type, method=method) as filename:
        if audio_type == "mp3":
            return _staged_file(filename, language)

        with transcoded_to_mp3(filename) as transcoded:
            return _staged_file(
                transcoded, language, orig_checksum=md5_checksum(filename)
            )


def _staged_file(source_file, language, orig_checksum=None):
    checksum = md5_checksum(source_file)
    dest_file = path.join(
        SAMPLE_DIR,
        "{language}/{language}-{checksum}.mp3".format(
            language=language, checksum=checksum
        ),
    )
    directory = path.dirname(dest_file)
    sh.mkdir("-p", directory)
    shutil.copy(source_file, dest_file)

    return StagedFile(dest_file, checksum, orig_checksum)


@contextmanager
def downloaded(url, suffix, method="wget"):
    print("      downloading {0}".format(url))
    with tempfile.NamedTemporaryFile(suffix=suffix) as t:
        if method == "wget":
            try:
                sh.wget("-e", "robots=off", "-U", DEFAULT_USER_AGENT, "-O", t.name, url)
            except sh.ErrorReturnCode_8:
                raise DownloadError(url)

        elif method == "requests":
            resp = requests.get(url)
            if not resp.status_code == 200:
                raise DownloadError(url)

            with open(t.name, "wb") as ostream:
                ostream.write(resp.content)

        else:
            raise ValueError("unsupported method {0}".format(method))

        yield t.name


@contextmanager
def transcoded_to_mp3(source_file):
    print("   transcoding to mp3...")
    with tempfile.NamedTemporaryFile(suffix=".mp3") as t:
        cmd = ["-i", source_file, "-c:a", "libmp3lame", "-ab", "256k", "-y", t.name]
        print("   ffmpeg {0}".format(" ".join(cmd)))
        sh.ffmpeg(*cmd)
        yield t.name


def _detect_audio_type(url):
    return urlparse(url).path.lower()[-3:]


def scan():
    "Return a set of urls and checksums that have already been indexed."
    seen = set()
    for f in glob.glob(path.join(INDEX_DIR, "*/*.json")):
        with open(f) as istream:
            r = json.load(istream)
            mark_as_seen(r, seen)

    return seen


def count():
    "Return the number of samples by language."
    dist = Counter()
    for f in glob.glob(path.join(INDEX_DIR, "*/*.json")):
        with open(f) as istream:
            r = json.load(istream)
            dist[r["language"]] += 1

    return dist


def mark_as_seen(sample, seen):
    seen.add(sample["source_url"])
    seen.add(sample["checksum"])
    seen.update(sample["media_urls"])

    if "origin_checksum" in sample:
        seen.add(sample["origin_checksum"])


def md5_checksum(filename):
    with open(filename, "rb") as istream:
        return hashlib.md5(istream.read()).hexdigest()


def load_schema():
    filename = path.join(INDEX_DIR, "schema.json")
    with open(filename) as istream:
        return json.load(istream)


def save(sample, schema=None):
    schema = schema or load_schema()
    jsonschema.validate(sample, schema)
    filename = path.join(
        INDEX_DIR, "{language}/{language}-{checksum}.json".format(**sample)
    )
    directory = path.dirname(filename)
    sh.mkdir("-p", directory)
    s = json.dumps(sample, indent=2, sort_keys=True)
    with open(filename, "w") as ostream:
        ostream.write(s)
