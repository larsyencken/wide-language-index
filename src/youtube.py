# -*- coding: utf-8 -*-
#
#  youtube.py
#  wide-language-index
#

"""
"""

import os
import tempfile
from typing import Dict
from urllib.parse import urlparse, parse_qs

from dateutil.parser import parse as parse_date
from apiclient.discovery import build
import requests

from audio import AudioSample
from sh import youtube_dl


YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'


def is_youtube_url(source_url: str) -> bool:
    return (source_url.startswith('https://www.youtube.com/watch')
            or is_short_url(source_url))


def is_short_url(url: str) -> bool:
    return url.startswith('https://youtu.be/')


def download_youtube_sample(source_url: str) -> AudioSample:
    "Download and transcode a YouTube video to audio."
    if is_short_url(source_url):
        short_url = source_url
        source_url = get_origin_url(short_url)

    metadata = fetch_youtube_metadata(source_url)

    t = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')

    output_template = os.path.splitext(t.name)[0] + '.%(ext)s'
    youtube_dl('-x', '--audio-format=mp3', '--output={}'.format(output_template),
               source_url)

    return AudioSample(tempfile=t, metadata=metadata)


def get_origin_url(short_url: str) -> str:
    resp = requests.head(short_url)
    if resp.status_code != 302:
        raise Exception('got status {} when unpacking youtube url'.format(resp.status_code))

    return resp.headers['Location']


def fetch_youtube_metadata(source_url: str) -> Dict[str, str]:
    youtube_id = get_video_id(source_url)

    youtube_api = build(YOUTUBE_API_SERVICE_NAME,
                        YOUTUBE_API_VERSION,
                        developerKey=os.environ['YOUTUBE_API_KEY'])

    response = youtube_api.videos().list(part='snippet',
                                         id=youtube_id).execute()

    item, = response['items']
    snippet = item['snippet']

    title = snippet['localized']['title']
    author = snippet['channelTitle']
    date = str(parse_date(snippet['publishedAt']).date())

    return {'title': title,
            'author': author,
            'source_url': source_url,
            'source_name': 'YouTube',
            'date': date}


def get_video_id(source_url):
    query = urlparse(source_url).query
    youtube_id, = parse_qs(query)['v']
    return youtube_id
