# -*- coding: utf-8 -*-
#
#  normalize.py
#  wide-language-index
#

"""
Reformat every JSON record so that they're all formatted consistently.
"""

import json
import glob


def normalize_json():
    n = 0
    for f in glob.glob('index/*/*.json') + ["data/rss_feeds.json"]:
        s = open(f).read()
        data = json.loads(s)
        s_norm = json.dumps(data, indent=2, sort_keys=True)

        if s != s_norm:
            print(f)
            with open(f, 'w') as ostream:
                ostream.write(s_norm)

            n += 1

    print(n, 'records changed')


if __name__ == '__main__':
    normalize_json()
