#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  audit.py
#  languagegame-data
#

"""
Audit the index and annotations to make sure they're consistent.

TODO
- Ensure languages are specified by their ISO code
- Ensure subfolders match the language code
- Recreate index for language game data
"""

from __future__ import absolute_import, print_function, division

import csv
import glob
import hashlib
import json
import os
import unittest
from typing import Callable

from clint.textui.colored import blue
import click
import jsonschema


VALID_LANGUAGES = set(r["id"] for r in json.load(open("ext/name_index_20140320.json")))

MACRO_LANGUAGES = set(
    r["Id"]
    for r in csv.DictReader(open("ext/iso-639-3.tab"), delimiter="\t")
    if r["Scope"] == "M"
)

OK_MACRO_LANGUAGES = set(
    [
        "nor",
        "sqi",
        "que",  # Quechua has many dialects, it's hard to get examples for one in particular
    ]
)


@click.command()
@click.option("--skip-audio", is_flag=True, help="Skip audit of audio samples.")
def main(skip_audio=False):
    """
    Check the integrity of the index, making sure all records are in the right
    format and containing the right fields. If audio is present, also audit
    the audio against checksums in the index.
    """
    audit_index()

    if not skip_audio:
        audit_samples()


def audit_index():
    print(blue("Auditing index..."))

    class IndexTestCase(unittest.TestCase):
        pass

    validator = make_validator()
    for i, f in enumerate(glob.glob("index/*/*.json")):
        t = make_test(f, i, validator)
        assert not hasattr(IndexTestCase, t.__name__)
        setattr(IndexTestCase, t.__name__, t)

    unittest.TextTestRunner().run(unittest.makeSuite(IndexTestCase))
    print()


def make_validator() -> Callable[[dict], None]:
    "Make a function that can validate sample records."
    sample_schema = json.load(open("index/sample.schema.json"))
    base_uri = "file://" + os.path.abspath("index") + "/"
    resolver = jsonschema.RefResolver(
        referrer=sample_schema,
        base_uri=base_uri,
    )
    validator = jsonschema.Draft4Validator(sample_schema, resolver=resolver)

    return validator.validate


def audit_samples():
    print(blue("Auditing samples..."))

    class SampleTestCase(unittest.TestCase):
        pass

    samples = sorted(glob.glob("samples/*/*.mp3"))
    for i, sample in enumerate(samples):
        t = make_sample_test(sample, i)
        assert not hasattr(SampleTestCase, t.__name__)
        setattr(SampleTestCase, t.__name__, t)

    unittest.TextTestRunner().run(unittest.makeSuite(SampleTestCase))
    print()


def make_test(f, i, validate):
    def t(self):
        blob = open(f).read()
        data = json.loads(blob)
        validate(data)

        # the language code is a valid ISO 693-3 code
        language = data.get("language")
        assert language in VALID_LANGUAGES, language

        # the language is not a macrolanguage
        assert language in OK_MACRO_LANGUAGES or language not in MACRO_LANGUAGES, (
            language
        )

        # the record is in the correct directory
        parent_dir = os.path.basename(os.path.dirname(f))
        self.assertEqual(parent_dir, language)

        # it is pretty-printed
        pretty_blob = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
        assert blob == pretty_blob, f

    name = "test_doc_{0}".format(i)
    t.__name__ = name
    return t


def make_sample_test(sample_file, i):
    def t(self):
        with open(sample_file, "rb") as istream:
            checksum = hashlib.md5(istream.read()).hexdigest()

        assert checksum in sample_file

    name = "test_sample_{0}".format(i)
    t.__name__ = name
    return t


if __name__ == "__main__":
    main()
