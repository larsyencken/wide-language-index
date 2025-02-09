# -*- coding: utf-8 -*-
#
#  fetch_rss_feed.py
#  wide-language-index
#

from collections import defaultdict
from urllib.parse import urlparse
import datetime as dt
import itertools
import json
import random

from pyquery import PyQuery as pq
import click
import feedparser

import index


RSS_FEEDS = "data/rss_feeds.json"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36"  # noqa


@click.command()
@click.option(
    "--max-per-feed", type=int, default=5, help="How many posts to fetch from each feed"
)
@click.option(
    "--language-cap",
    type=int,
    default=50,
    help="How many entries per language before we stop fetching new ones.",
)
@click.option("--language", default=None, help="Only scrape the given language code.")
def main(max_per_feed=5, language_cap=50, language=None):
    """
    Fetch new audio podcasts from rss feeds and add them to the index.
    """
    feeds = load_feeds()
    count = index.count()
    seen = index.scan()

    languages = (
        sorted([l for l in feeds if count[l] < language_cap])
        if language is None
        else [language]
    )

    for l in languages:
        for p in iter_language_posts(l, feeds[l], max_per_feed):
            if is_good_post(p, seen):
                ok = save_post(p, seen)
                count[l] += ok

                if count[l] >= language_cap:
                    break


def load_feeds():
    "Return a randomized list of feeds by language."
    with open(RSS_FEEDS) as istream:
        data = json.load(istream)

    by_lang = defaultdict(list)
    for feed in data:
        by_lang[feed["language"]].append(feed)

    for v in by_lang.values():
        random.shuffle(v)

    return by_lang


def iter_language_posts(language, feeds, max_per_post):
    yield from itertools.chain(
        *(itertools.islice(iter_feed_posts(f), max_per_post) for f in feeds)
    )


def iter_feed_posts(feed):
    rss_url = feed["rss_url"]
    rss = feedparser.parse(rss_url)
    for i, e in enumerate(rss.entries):
        title = e["title"]
        print(
            "[{0}] {1}: {2}".format(
                feed["language"],
                feed["source_name"],
                title,
            )
        )
        media_url = detect_media_url(e, feed)
        source_url = e.get("link", media_url)

        t = e["published_parsed"]
        d = dt.date(year=t.tm_year, month=t.tm_mon, day=t.tm_mday)
        yield {
            "title": title,
            "media_urls": [media_url],
            "source_url": source_url,
            "date": str(d),
            "language": feed["language"],
            "source_name": feed["source_name"],
        }


def detect_media_url(episode, feed):
    for strategy in [use_episode_link, use_audio_enclosure, follow_episode_link]:
        media_url = strategy(episode, feed)
        if media_url is not None:
            return media_url

    raise Exception("no audio found for this podcast")


def use_episode_link(e, feed):
    if "link" in e and e["link"].endswith(".mp3"):
        return e["link"]


def use_audio_enclosure(e, feed):
    if "links" in e:
        audio_links = [
            l["href"] for l in e["links"] if "href" in l and is_audio_url(l["href"])
        ]
        if audio_links:
            if len(audio_links) > 1 and "multiple_audio" not in feed:
                raise Exception("too many audio files to choose from: {0}".format(e))

            return audio_links[0]


def follow_episode_link(e, feed):
    if "link" not in e:
        return

    allow_multiple = "multiple_audio" in feed
    return get_audio_link(e["link"], allow_multiple=allow_multiple)


def get_audio_link(url, allow_multiple=False):
    d = pq(url=url)
    files = [
        a.attrib["href"]
        for a in d("a")
        if "href" in a.attrib and is_audio_url(a.attrib["href"])
    ]
    if files:
        if len(set(files)) > 1 and not allow_multiple:
            raise Exception("too many audio files to choose from: {0}".format(url))

        return list(files)[0]


def is_audio_url(url):
    return urlparse(url).path.lower()[-4:] in (".mp3", ".m4a")


def is_good_post(p, seen):
    return p["source_url"] not in seen and p["media_urls"][0] not in seen


def save_post(sample, seen):
    (media_url,) = sample["media_urls"]

    try:
        staged = index.stage_audio(media_url, sample["language"])
    except index.DownloadError:
        print("      SKIPPING: got 404 when downloading")
        return False

    sample["checksum"] = staged.checksum
    if staged.checksum in seen:
        print("      SKIPPING: checksum already in index")
        return False

    if staged.orig_checksum:
        sample["origin_checksum"] = staged.orig_checksum
        if staged.orig_checksum in seen:
            print("      SKIPPING: checksum already in index")
            return False

    index.save(sample)
    index.mark_as_seen(sample, seen)
    return True


if __name__ == "__main__":
    main()
