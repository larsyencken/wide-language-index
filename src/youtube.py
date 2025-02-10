# -*- coding: utf-8 -*-
import os
import re
import tempfile
import urllib.parse
from datetime import datetime
from typing import Dict

import yt_dlp

from audio import AudioSample


class YouTubeError(Exception):
    """Base exception for YouTube-related errors."""

    pass


def is_youtube_url(url: str) -> bool:
    """Check if a URL is a YouTube video URL."""
    patterns = [
        r"^https?://(?:www\.)?youtube\.com/watch\?.*v=[\w-]+",
        r"^https?://youtu\.be/[\w-]+",
        r"^https?://(?:www\.)?youtube\.com/shorts/[\w-]+",
    ]
    return any(re.match(pattern, url) for pattern in patterns)


def get_video_id(url: str) -> str:
    """Extract the video ID from a YouTube URL."""
    if "youtube.com/watch" in url:
        query = urllib.parse.urlparse(url).query
        params = urllib.parse.parse_qs(query)
        return params["v"][0]
    elif "youtu.be/" in url:
        return url.split("/")[-1].split("?")[0]
    elif "youtube.com/shorts/" in url:
        return url.split("/")[-1].split("?")[0]
    raise YouTubeError(f"Could not extract video ID from URL: {url}")


def download_youtube_sample(url: str) -> AudioSample:
    """Download a YouTube video's audio track and return it as an AudioSample."""
    # First get the metadata
    metadata = fetch_youtube_metadata(url)

    # Create a temporary file for the audio
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()

    # Configure yt-dlp options
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": temp_file.name,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise YouTubeError(f"Failed to download audio: {str(e)}")

    # Reopen the temp file for the AudioSample
    return AudioSample(
        tempfile=tempfile.NamedTemporaryFile(delete=False), metadata=metadata
    )


def fetch_youtube_metadata(url: str) -> Dict[str, str]:
    """Fetch metadata for a YouTube video using yt-dlp."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Convert upload date to ISO format
            upload_date = info.get("upload_date")
            if upload_date:
                date = datetime.strptime(upload_date, "%Y%m%d").date().isoformat()
            else:
                date = datetime.now().date().isoformat()

            return {
                "title": info.get("title", ""),
                "author": info.get("uploader", ""),
                "source_url": url,
                "source_name": "YouTube",
                "date": date,
            }
    except Exception as e:
        raise YouTubeError(f"Failed to fetch metadata: {str(e)}")
