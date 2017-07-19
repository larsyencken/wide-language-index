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

import youtube_dl
from dateparse.parser import parse as parse_date
from apiclient.discovery import build

from types import AudioSample


YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'


def is_youtube_url(source_url: str) -> bool:
    return source_url.startswith('https://www.youtube.com/watch')


def download_youtube_sample(source_url: str) -> AudioSample:
    "Download and transcode a YouTube video to audio."
    metadata = fetch_youtube_metadata(source_url)

    t = tempfile.NamedTemporaryFile(delete=False)

    opts = {
        'outtmpl': t.name,
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(opts) as ydl:
        ydl.download([source_url])

    return AudioSample(t, metadata)


def fetch_youtube_metadata(source_url: str) -> Dict[str, str]:
    youtube_id = get_video_id(source_url)

    youtube_api = build(YOUTUBE_API_SERVICE_NAME,
                        YOUTUBE_API_VERSION,
                        developerKey=os.environ['YOUTUBE_API_KEY'])

    response = youtube_api.search().list(part='snippet',
                                         relatedToVideoId=youtube_id,
                                         type='video').execute()

    item, = response.json()['items']
    snippet = item['snippet']

    title = snippet['localized']['title']
    author = snippet['channelTitle']
    date = parse_date(snippet['publisedAt']).date()

    return {'title': title,
            'author': author,
            'source_url': source_url,
            'date': date}


def get_video_id(source_url):
    query = urlparse(source_url).query
    youtube_id, = parse_qs(query)['v']
    return youtube_id
