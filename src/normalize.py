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

import click


@click.command()
def normalize_json_files():
    """
    Make sure all JSON is identically formatted.
    """
    n = 0
    for f in glob.glob('index/*/*.json') + ["data/rss_feeds.json"]:
        n += normalize_file(f)

    print(n, 'records changed')


def normalize_file(f):
    s = open(f).read()
    data = json.loads(s)

    if 'media_urls' in data:
        data['media_urls'] = remove_duplicates(data['media_urls'])

    if isinstance(data, list):
        data.sort(key=lambda r: r['language'])

    s_norm = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)

    if s != s_norm:
        print(f)
        with open(f, 'w') as ostream:
            ostream.write(s_norm)

        return True

    return False


def remove_duplicates(xs):
    seen = set()
    ys = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            ys.append(x)

    return ys


if __name__ == '__main__':
    normalize_json_files()
