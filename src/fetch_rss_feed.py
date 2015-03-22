# -*- coding: utf-8 -*-
#
#  fetch_rss_feed.py
#  wide-language-index
#

import os
import json
import datetime as dt
import hashlib
import tempfile
import shutil
import glob
from urllib.parse import urlparse

import click
import feedparser
import jsonschema
import sh
from pyquery import PyQuery as pq


RSS_FEEDS = 'data/rss_feeds.json'


class DownloadError(Exception):
    pass


@click.command()
@click.option('--max-posts', type=int, default=5,
              help='How many posts to fetch from each feed')
@click.option('--language', default=None,
              help='Only scrape the given language code.')
def main(max_posts=5, language=None):
    """
    Fetch new audio podcasts from rss feeds and add them to the index.
    """
    feeds = load_config()
    schema = load_schema()
    seen = scan_index()
    for feed in feeds:
        if language in (feed['language'], None):
            fetch_posts(feed, max_posts, schema, seen)


def load_schema():
    with open('index/schema.json') as istream:
        return json.load(istream)


def fetch_posts(feed, max_posts, schema, seen):
    print('[{0}] {1}'.format(feed['language'], feed['source_name']))

    for post in iter_feed(feed, max_posts, seen):
        sample = post.copy()
        sample['language'] = feed['language']
        sample['source_name'] = feed['source_name']
        try:
            fetch_sample(sample)

        except DownloadError:
            print('got 404 when downloading -- skipping')
            continue

        if sample['checksum'] in seen:
            print('checksum already in index -- skipping')
            continue

        save_record(sample)
        jsonschema.validate(sample, schema)

        seen.add(sample['source_url'])
        seen.add(sample['checksum'])

    print()


def fetch_sample(sample):
    url, = sample['media_urls']
    with tempfile.NamedTemporaryFile(suffix='.mp3') as t:
        try:
            sh.wget('-O', t.name, url)
        except sh.ErrorReturnCode_8:
            raise DownloadError(url)

        checksum = md5_checksum(t.name)
        sample['checksum'] = checksum
        filename = 'samples/{language}/{language}-{checksum}.mp3'.format(
            **sample
        )
        directory = os.path.dirname(filename)
        sh.mkdir('-p', directory)
        shutil.copy(t.name, filename)


def save_record(sample):
    filename = 'index/{language}/{language}-{checksum}.json'.format(**sample)
    directory = os.path.dirname(filename)
    sh.mkdir('-p', directory)
    s = json.dumps(sample, indent=2, sort_keys=True)
    with open(filename, 'w') as ostream:
        ostream.write(s)


def md5_checksum(filename):
    with open(filename, 'rb') as istream:
        return hashlib.md5(istream.read()).hexdigest()


def scan_index():
    seen = set()
    for f in glob.glob('index/*/*.json'):
        with open(f) as istream:
            r = json.load(istream)
            seen.add(r['source_url'])
            seen.add(r['checksum'])

    return seen


def iter_feed(feed, max_posts, seen_urls):
    rss_url = feed['rss_url']
    rss = feedparser.parse(rss_url)
    for i, e in enumerate(rss.entries[:max_posts]):
        title = e['title']
        media_url = detect_media_url(e, feed)
        source_url = e.get('link', media_url)

        if source_url in seen_urls:
            print('{0}. {1} (skipped)'.format(i + 1, title))
            continue

        print('{0}. {1}'.format(i + 1, title))
        t = e['published_parsed']
        d = dt.date(year=t.tm_year, month=t.tm_mon, day=t.tm_mday)
        yield {
            'title': title,
            'media_urls': [media_url],
            'source_url': source_url,
            'date': str(d),
        }


def detect_media_url(e, feed):
    # firstly, try the link element
    if 'link' in e and e['link'].endswith('.mp3'):
        return e['link']

    # next try an audio enclosure
    if 'links' in e:
        audio_links = [l['href'] for l in e['links']
                       if is_mp3_url(l['href'])]
        if audio_links:
            if len(audio_links) > 1 and 'multiple_audio' not in feed:
                raise Exception('too many audio files to choose from: '
                                '{0}'.format(e))

            return audio_links[0]

    # try following the link, and see if there's an audio file on that page
    if 'link' in e:
        d = pq(url=e['link'])
        files = [a.attrib['href'] for a in d('a')
                 if 'href' in a.attrib
                 and is_mp3_url(a.attrib['href'])]
        if files:
            if len(set(files)) > 1 and 'multiple_audio' not in feed:
                raise Exception('too many audio files to choose from: '
                                '{0}'.format(e['link']))

            return list(files)[0]

    raise Exception('no audio found for this podcast')


def is_mp3_url(url):
    return urlparse(url).path.lower().endswith('.mp3')


def load_config():
    with open(RSS_FEEDS) as istream:
        return json.load(istream)


if __name__ == '__main__':
    main()
