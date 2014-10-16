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


def audit_index():
    print(blue('Auditing index...'))
    schema = json.load(open('index/schema.json'))

    class IndexTestCase(unittest.TestCase):
        pass

    for i, f in enumerate(glob.glob('index/*/*.json')):
        t = make_test(f, i, schema)
        assert not hasattr(IndexTestCase, t.__name__)
        setattr(IndexTestCase, t.__name__, t)

    unittest.TextTestRunner().run(unittest.makeSuite(IndexTestCase))
    print()


def make_test(f, i, schema):
    def t(self):
        blob = open(f).read()
        data = json.loads(blob)
        jsonschema.validate(data, schema)

        # the language code is a valid ISO 693-3 code
        language = data.get('language')
        assert language in VALID_LANGUAGES, language

        # the record is in the correct directory
        parent_dir = os.path.basename(os.path.dirname(f))
        self.assertEqual(parent_dir, language)

        # it is pretty-printed
        pretty_blob = json.dumps(data, indent=2, sort_keys=True)
        assert blob == pretty_blob

    name = 'test_doc_{0}'.format(i)
    t.__name__ = name
    return t


if __name__ == '__main__':
    main()
