#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  fetch_index.py
#  wide-langauge-index
#

"""
Download the actual sample files for the language game index.
"""

from __future__ import annotations  # More modern future import

import asyncio
import glob
import hashlib
import json
import os
from asyncio import Queue, Semaphore  # Replace queue with asyncio.Queue
from os import path
from typing import AsyncIterator, Dict, List

import aiofiles
import aiohttp
import click

INDEX_DIR = path.normpath(path.join(path.dirname(__file__), "..", "index"))
SAMPLE_DIR = path.normpath(path.join(path.dirname(__file__), "..", "samples"))
TOMBSTONE = None


async def async_fetch_index(
    index_dir=INDEX_DIR, output_dir=SAMPLE_DIR, language=None, prefer_mirrors=False
):
    """
    Fetch a copy of every sample in the index, placing them in output_dir.
    """
    records = iter_records(index_dir, output_dir, language=language)
    to_fetch: Queue = Queue()

    await enqueue_missing(records, to_fetch)
    await fetch_missing(to_fetch, prefer_mirrors=prefer_mirrors)


async def enqueue_missing(records, q: Queue) -> None:
    print("Checking for missing samples...")
    pending = []

    for r in records:
        lang = r["language"]
        checksum = r["checksum"]
        dest_file = r["dest_file"]

        if not os.path.exists(dest_file):
            await q.put(r)
            continue

        while len(pending) > 10:
            await asyncio.sleep(0.1)

        pending.append(r)
        task = asyncio.create_task(file_has_checksum(r["dest_file"], checksum))
        task.add_done_callback(lambda x, r=r: on_checksum_complete(x, r, q, pending))

    while pending:
        await asyncio.sleep(0.1)


def on_checksum_complete(
    future: asyncio.Future, record: Dict, q: Queue, pending: List
) -> None:
    if not future.result():
        q.put_nowait(record)
    pending.remove(record)


async def fetch_missing(q: Queue, prefer_mirrors: bool = False) -> None:
    print("Fetching missing samples...")
    pending = Semaphore(20)

    while not q.empty():
        r = await q.get()

        print("{:5s} {}".format("FETCH", r["dest_file"]))
        async with pending:
            await fetch_with_retry(r, prefer_mirrors=prefer_mirrors)

    # Wait for remaining tasks
    while pending._value < 20:
        await asyncio.sleep(0.1)


async def fetch_with_retry(r: Dict, prefer_mirrors: bool = False) -> None:
    checksum = r["checksum"]
    dest_file = r["dest_file"]
    media_urls = r["media_urls"][:]

    if prefer_mirrors:
        media_urls.reverse()

    async with aiohttp.ClientSession() as session:
        for media_url in media_urls:
            try:
                await download_and_validate(session, media_url, checksum, dest_file)
                print("{:5s} {}".format("DONE", r["dest_file"]))
                return

            except DownloadError as e:
                print(f"Error downloading {media_url}: {e}")
                continue

    print("{:5s} {}".format("FAIL", dest_file))


def iter_records(
    index_dir: str, output_dir: str, language: str = None
) -> AsyncIterator[Dict]:
    if language is None:
        pattern = "{0}/*/*.json".format(index_dir)
    else:
        pattern = "{0}/{1}/*.json".format(index_dir, language)

    filenames = sorted(glob.glob(pattern))

    for f in filenames:
        with open(f) as istream:
            r = json.load(istream)
            lang = r["language"]
            checksum = r["checksum"]

            # e.g. samples/fra/fra-8da6ee6728fa1f38c99e16585752ccaa.mp3
            r["dest_file"] = os.path.join(
                output_dir, lang, "{0}-{1}.mp3".format(lang, checksum)
            )

            yield r


class DownloadError(Exception):
    pass


async def file_has_checksum(filename: str, checksum: str) -> bool:
    if not os.path.exists(filename):
        return False

    async with aiofiles.open(filename, "rb") as istream:
        data = await istream.read()
        return hashlib.md5(data).hexdigest() == checksum


async def download_and_validate(
    session: aiohttp.ClientSession, url: str, checksum: str, dest_file: str
) -> None:
    url = url.replace(
        "mirror.widelanguageindex.org",
        "s3.us-east-1.amazonaws.com/mirror.widelanguageindex.org",
    )
    data = await download(session, url)
    c = hashlib.md5(data).hexdigest()
    if c != checksum:
        raise DownloadError(
            "checksum mismatch downloading {0} -- got {1}".format(
                url,
                c,
            )
        )

    parent_dir = os.path.dirname(dest_file)
    if not os.path.isdir(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    async with aiofiles.open(dest_file, "wb") as ostream:
        await ostream.write(data)


async def download(session: aiohttp.ClientSession, url: str) -> bytes:
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise DownloadError(f"got HTTP {resp.status} downloading {url}")
            return await resp.read()
    except aiohttp.ClientError as e:
        raise DownloadError(f"Error downloading {url}: {str(e)}")


@click.command()
@click.option("--index-dir", default=INDEX_DIR, help="Use a different index folder.")
@click.option("--output-dir", default=SAMPLE_DIR, help="Use a different output folder.")
@click.option("--language", help="Only fetch the given language.")
@click.option(
    "--prefer-mirrors", is_flag=True, help="Try mirrors before the original source."
)
def fetch_index(
    index_dir=INDEX_DIR, output_dir=SAMPLE_DIR, language=None, prefer_mirrors=False
):
    """
    Fetch a copy of every sample in the index, placing them in output_dir.
    """
    asyncio.run(async_fetch_index(index_dir, output_dir, language, prefer_mirrors))


if __name__ == "__main__":
    fetch_index()
