# -*- coding: utf-8 -*-
#
#  fetch_rss_feed.py
#  wide-language-index
#

import json
import datetime as dt
from urllib.parse import urlparse

import click
import feedparser
from pyquery import PyQuery as pq

import index


RSS_FEEDS = 'data/rss_feeds.json'
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36'  # noqa


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
    schema = index.load_schema()
    seen = index.scan()
    for feed in feeds:
        if language in (feed['language'], None):
            fetch_posts(feed, max_posts, schema, seen)


def fetch_posts(feed, max_posts, schema, seen):
    print('[{0}] {1}'.format(feed['language'], feed['source_name']))

    for post in iter_feed(feed, max_posts, seen):
        sample = post.copy()
        sample.update({
            'language': feed['language'],
            'source_name': feed['source_name'],
        })

        media_url = sample['media_urls'][0]
        try:
            _, checksum = index.stage_audio(media_url,
                                            feed['language'])
        except index.DownloadError:
            print('SKIPPING: got 404 when downloading')
            continue

        sample['checksum'] = checksum
        if checksum in seen:
            print('SKIPPING: checksum already in index')
            continue

        index.save(sample, schema=schema)
        index.mark_as_seen(sample, seen)

    print()


def iter_feed(feed, max_posts, seen):
    rss_url = feed['rss_url']
    rss = feedparser.parse(rss_url)
    for i, e in enumerate(rss.entries[:max_posts]):
        title = e['title']
        media_url = detect_media_url(e, feed)
        source_url = e.get('link', media_url)

        if source_url in seen or media_url in seen:
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


def detect_media_url(episode, feed):
    for strategy in [use_episode_link,
                     use_audio_enclosure,
                     follow_episode_link]:
        media_url = strategy(episode, feed)
        if media_url is not None:
            return media_url

    raise Exception('no audio found for this podcast')


def use_episode_link(e, feed):
    if 'link' in e and e['link'].endswith('.mp3'):
        return e['link']


def use_audio_enclosure(e, feed):
    if 'links' in e:
        audio_links = [l['href'] for l in e['links']
                       if is_mp3_url(l['href'])]
        if audio_links:
            if len(audio_links) > 1 and 'multiple_audio' not in feed:
                raise Exception('too many audio files to choose from: '
                                '{0}'.format(e))

            return audio_links[0]


def follow_episode_link(e, feed):
    if 'link' not in e:
        return

    allow_multiple = ('multiple_audio' in feed)
    return get_audio_link(e['link'], allow_multiple=allow_multiple)


def get_audio_link(url, allow_multiple=False):
    d = pq(url=url)
    files = [a.attrib['href'] for a in d('a')
             if 'href' in a.attrib
             and is_mp3_url(a.attrib['href'])]
    if files:
        if len(set(files)) > 1 and not allow_multiple:
            raise Exception('too many audio files to choose from: '
                            '{0}'.format(url))

        return list(files)[0]


def is_mp3_url(url):
    return urlparse(url).path.lower().endswith('.mp3')


def load_config():
    with open(RSS_FEEDS) as istream:
        return json.load(istream)


if __name__ == '__main__':
    main()
