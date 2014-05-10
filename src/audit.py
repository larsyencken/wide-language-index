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

import os
import json
import glob
import unittest
from clint.textui.colored import blue

import jsonschema


VALID_LANGUAGES = set(
    r['id'] for r in json.load(open('ext/name_index_20140320.json'))
)


def main():
    audit_index()
    audit_annotations()


def audit_index():
    print(blue('Auditing index...'))
    schema = json.load(open('index/schema.json'))

    class IndexTestCase(unittest.TestCase):
        pass

    for i, f in enumerate(glob.glob('index/*/*.json')):
        def t(self):
            data = json.load(open(f))
            jsonschema.validate(data, schema)

            language = data.get('language')
            assert language in VALID_LANGUAGES, language
            parent_dir = os.path.basename(os.path.dirname(f))
            assert parent_dir == language

        name = 'test_doc_{0}'.format(i)
        t.__name__ = name
        setattr(IndexTestCase, name, t)

    unittest.TextTestRunner().run(unittest.makeSuite(IndexTestCase))
    print()


def audit_annotations():
    print(blue('Auditing annotations...'))
    schema = json.load(open('annotations/schema.json'))

    class AnnotationTestCase(unittest.TestCase):
        pass

    for i, f in enumerate(glob.glob('annotations/*/*.json')):
        def t(self):
            data = json.load(open(f))
            jsonschema.validate(data, schema)

            language = data.get('language')
            assert language in VALID_LANGUAGES, language
            parent_dir = os.path.basename(os.path.dirname(f))
            assert parent_dir == language

        name = 'test_doc_{0}'.format(i)
        t.__name__ = name
        setattr(AnnotationTestCase, name, t)

    unittest.TextTestRunner().run(unittest.makeSuite(AnnotationTestCase))
    print()


if __name__ == '__main__':
    main()
