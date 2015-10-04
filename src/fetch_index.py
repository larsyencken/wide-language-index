#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  fetch_index.py
#  wide-langauge-index
#

"""
Download the actual sample files for the language game index.
"""

from __future__ import absolute_import, print_function, division

import asyncio
from os import path
import glob
import hashlib
import json
import os

import aiohttp
import aiofiles
import click
import queue


INDEX_DIR = path.normpath(path.join(path.dirname(__file__),
                                    '..', 'index'))
SAMPLE_DIR = path.normpath(path.join(path.dirname(__file__),
                                     '..', 'samples'))
TOMBSTONE = None


@click.command()
@click.option('--index-dir', default=INDEX_DIR,
              help='Use a different index folder.')
@click.option('--output-dir', default=SAMPLE_DIR,
              help='Use a different output folder.')
@click.option('--language', help='Only fetch the given language.')
@click.option('--prefer-mirrors', is_flag=True,
              help='Try mirrors before the original source.')
def fetch_index(index_dir=INDEX_DIR, output_dir=SAMPLE_DIR, language=None,
                prefer_mirrors=False):
    """
    Fetch a copy of every sample in the index, placing them in output_dir.
    """
    records = iter_records(index_dir, output_dir, language=language)

    to_fetch = queue.Queue()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(enqueue_missing(records, to_fetch))
    loop.run_until_complete(fetch_missing(to_fetch,
                                          prefer_mirrors=prefer_mirrors))
    loop.close()


async def enqueue_missing(records, q):
    print('Checking for missing samples...')
    pending = []

    for r in records:
        lang = r['language']
        checksum = r['checksum']
        dest_file = r['dest_file']

        if not os.path.exists(dest_file):
            q.put(r)
            continue

        while len(pending) > 10:
            await asyncio.sleep(0.1)

        pending.append(r)
        f = asyncio.ensure_future(
            file_has_checksum(r['dest_file'], checksum)
        )
        f.add_done_callback(
            lambda x: on_checksum_complete(x, dest_file, q, pending)
        )

    while pending:
        await asyncio.sleep(0.1)


def on_checksum_complete(f, dest_file, q, pending):
    if not f.result():
        q.put(r)

    pending.pop()


async def fetch_missing(q, prefer_mirrors=False):
    print('Fetching missing samples...')
    pending = asyncio.Semaphore(20)
    while not q.empty():
        r = q.get()

        print('{:5s} {}'.format('FETCH', r['dest_file']))
        await pending.acquire()
        f = asyncio.ensure_future(
            fetch_with_retry(r, prefer_mirrors=prefer_mirrors)
        )
        f.add_done_callback(lambda f: pending.release())

    while pending._value < 20:
        await asyncio.sleep(0.1)


async def fetch_with_retry(r, prefer_mirrors=False):
    checksum = r['checksum']
    dest_file = r['dest_file']
    media_urls = r['media_urls'][:]

    if prefer_mirrors:
        media_urls.reverse()

    for media_url in media_urls:
        try:
            await download_and_validate(media_url, checksum, dest_file)
            print('{:5s} {}'.format('DONE', r['dest_file']))
            return

        except DownloadError as e:
            pass

    print('{:5s} {}'.format('FAIL', dest_file))


def iter_records(index_dir, output_dir, language=None):
    if language is None:
        pattern = '{0}/*/*.json'.format(index_dir)
    else:
        pattern = '{0}/{1}/*.json'.format(index_dir, language)

    filenames = sorted(glob.glob(pattern))

    for f in filenames:
        with open(f) as istream:
            r = json.load(istream)
            lang = r['language']
            checksum = r['checksum']

            # e.g. samples/fra/fra-8da6ee6728fa1f38c99e16585752ccaa.mp3
            r['dest_file'] = os.path.join(output_dir, lang,
                                          '{0}-{1}.mp3'.format(lang, checksum))

            yield r


class DownloadError(Exception):
    pass


async def file_has_checksum(filename, checksum):
    if not os.path.exists(filename):
        return False

    istream = await aiofiles.open(filename, 'rb')
    try:
        data = await istream.read()
        return hashlib.md5(data).hexdigest() == checksum
    finally:
        await istream.close()


async def download_and_validate(url, checksum, dest_file):
    data = await download(url)
    c = hashlib.md5(data).hexdigest()
    if c != checksum:
        raise DownloadError(
            'checksum mismatch downloading {0} -- got {1}'.format(
                url,
                c,
            )
        )

    parent_dir = os.path.dirname(dest_file)
    if not os.path.isdir(parent_dir):
        os.mkdir(parent_dir)

    ostream = await aiofiles.open(dest_file, 'wb')
    try:
        await ostream.write(data)
    finally:
        await ostream.close()


async def download(url):
    try:
        resp = await aiohttp.request('GET', url)
    except aiohttp.errors.ClientOSError:
        raise DownloadError('could not connect downloading {}'.format(
            url,
        ))

    status = resp.status
    if status != 200:
        resp.close()
        raise DownloadError('got HTTP {0} downloading {1}'.format(
            status,
            url,
        ))
    data = await resp.read()
    return data


if __name__ == '__main__':
    fetch_index()
