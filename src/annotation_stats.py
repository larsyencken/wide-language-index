#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  annotation_stats.py
#  wide-language-index
#

"""
Generate a markdown document of annotation statistics.
"""

import json
import collections
import glob

import click


TEMPLATE_PAGE = '''# Annotation statistics

## Overall

- Annotations: {good_annotations} good + {bad_annotations} bad = {total_annotations} total
- Languages:
    - {num_1_annotations} with >=1 annotations
    - {num_5_annotations} with >=5 annotations
    - {num_10_annotations} with >=10 annotations

## By language

{per_language_stats}
'''  # noqa

TEMPLATE_LANGUAGE = '- [{code}] {name}: {good_annotations} good/{total_annotations} total'  # noqa


@click.command()
@click.argument('output_file')
def annotation_stats(output_file):
    """
    Generate a summary of annotation statistics for each language in Markdown.
    """
    metadata = load_metadata()
    languages = load_language_names()

    summary = generate_summary(metadata, languages)
    write_summary(summary, output_file)


def load_metadata():
    metadata = collections.defaultdict(list)
    for f in glob.glob('index/*/*.json'):
        with open(f) as istream:
            rec = json.load(istream)
            lang = rec['language']
            metadata[lang].append(rec)

    return metadata


def load_language_names():
    name_index = json.load(open('ext/name_index_20140320.json'))
    return {r['id']: r['print_name']
            for r in name_index}


def generate_summary(metadata, languages):
    stats = overall_stats(metadata)
    per_language = per_language_stats(metadata, languages)

    per_language_markdown = '\n'.join(
        TEMPLATE_LANGUAGE.format(**record)
        for record in per_language
    )
    stats['per_language_stats'] = per_language_markdown
    return TEMPLATE_PAGE.format(**stats)


def overall_stats(metadata):
    good_annotations = count_annotations(metadata, 'good')
    bad_annotations = count_annotations(metadata, 'bad')
    total_annotations = good_annotations + bad_annotations

    num_1_annotations = 0
    num_5_annotations = 0
    num_10_annotations = 0

    for lang, samples in metadata.items():
        n_good = count_lang_annotations(samples, 'good')

        if n_good >= 1:
            num_1_annotations += 1

        if n_good >= 5:
            num_5_annotations += 1

        if n_good >= 10:
            num_10_annotations += 1

    return locals()


def per_language_stats(metadata, code_to_name):
    stats = []
    for lang, samples in metadata.items():
        record = {
            'code': lang,
            'name': code_to_name[lang],
            'good_annotations': count_lang_annotations(samples, 'good'),
            'total_annotations': count_lang_annotations(samples),
        }
        stats.append(record)

    stats.sort(key=lambda r: (-r['good_annotations'], r['code']))
    return stats


def count_lang_annotations(samples, label=None):
    return sum(label is None or a['label'] == label
               for sample in samples
               for a in sample.get('annotations', []))


def count_annotations(metadata, label=None):
    return sum(count_lang_annotations(samples, label)
               for samples in metadata.values())


def iter_annotations(metadata):
    for samples in metadata.values():
        for sample in samples:
            yield from sample.get('annotations', [])


def write_summary(content, filename):
    with open(filename, 'w') as ostream:
        ostream.write(content)


if __name__ == '__main__':
    annotation_stats()
