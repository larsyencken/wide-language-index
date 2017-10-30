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

from audio import AudioSample
from sh import youtube_dl


YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'


def is_youtube_url(source_url: str) -> bool:
    return source_url.startswith('https://www.youtube.com/watch')


def download_youtube_sample(source_url: str) -> AudioSample:
    "Download and transcode a YouTube video to audio."
    metadata = fetch_youtube_metadata(source_url)

    t = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')

    output_template = os.path.splitext(t.name)[0] + '.%(ext)s'
    youtube_dl('-x', '--audio-format=mp3', '--output={}'.format(output_template),
               source_url)

    return AudioSample(tempfile=t, metadata=metadata)


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
