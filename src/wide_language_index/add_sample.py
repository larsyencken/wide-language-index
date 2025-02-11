#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simplify adding a sample to the index with expanded audio format support.
"""

import hashlib
import json
import os
import shutil
import subprocess as sp
import sys
import tempfile
from os import path
from typing import Any, Dict

import click
import dotenv
import sh

from . import youtube
from .audio import AudioSample

dotenv.load_dotenv()
BASE_DIR = path.abspath(path.join(path.dirname(__file__), ".."))
INDEX_DIR = path.join(BASE_DIR, "index")
SAMPLE_DIR = path.join(BASE_DIR, "samples")

# Expanded list of supported input formats
SUPPORTED_FORMATS = {
    "mp3",
    "m4a",
    "wav",
    "ogg",
    "flac",
    "aac",
    "wma",
    "aiff",
    "m4b",
    "opus",
    "webm",
}

TEMPLATE = {
    "checksum": "",
    "date": "",
    "language": "",
    "media_urls": [],
    "source_name": "",
    "source_url": "",
}

NO_METADATA = {}


@click.command()
@click.argument("language")
@click.argument("source_url")
@click.option("--edit", is_flag=True, help="Open the new record in an editor")
@click.option("--mirror", is_flag=True, help="Mirror the sample to S3")
def main(language: str, source_url: str, edit: bool = False, mirror: bool = False):
    """
    Add a single language example to the index.
    Supports an expanded range of audio formats that are transcoded to MP3.
    """
    filename = add_sample(language, source_url)

    if edit:
        open_in_editor(filename)


def add_sample(language: str, source_url: str) -> str:
    """Add a new audio sample to the index."""
    sample = fetch_sample(source_url)
    checksum = checksum_sample(sample)
    file_sample(language, checksum, sample)
    filename = make_stub_record(language, checksum, source_url, sample.metadata)
    return filename


def fetch_sample(source_url: str) -> AudioSample:
    """Ingest the sample to a local temporary file."""
    if is_url(source_url):
        if youtube.is_youtube_url(source_url):
            sample = youtube.download_youtube_sample(source_url)
        else:
            sample = download_sample(source_url)
    else:
        sample = copy_sample(source_url)

    # Transcode if not already MP3
    if not is_mp3(sample.filename):
        sample = transcode_to_mp3(sample)

    return sample


def is_mp3(filename: str) -> bool:
    """Check if a file is already in MP3 format."""
    return filename.lower().endswith(".mp3")


def detect_audio_format(filename: str) -> str:
    """Detect the audio format from the file extension."""
    ext = path.splitext(filename)[1].lower().lstrip(".")
    return ext if ext in SUPPORTED_FORMATS else None


def transcode_to_mp3(sample: AudioSample) -> AudioSample:
    """Transcode any supported audio format to MP3."""
    # Get format from metadata if available, otherwise try to detect from filename
    source_format = sample.metadata.get("original_format")
    if not source_format:
        source_format = detect_audio_format(sample.metadata.get("source_url", ""))
        if not source_format:
            raise ValueError(
                f"Could not determine audio format for: {sample.metadata.get('source_url', 'unknown source')}"
            )

    if source_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported audio format: {source_format}")

    # Close the input file if it's still open
    if not sample.tempfile.closed:
        sample.tempfile.close()
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_out:
        output_path = temp_out.name

    try:
        # Use ffmpeg for transcoding with high quality settings and force non-interactive mode
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files without asking
            "-i",
            sample.filename,
            "-c:a",
            "libmp3lame",
            "-q:a",
            "0",  # Best quality
            "-map",
            "a",  # Audio only
            "-nostdin",  # Disable interaction on standard input
            output_path,
        ]
        # Run with pipes for stdout/stderr and suppress console window
        process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, stdin=sp.DEVNULL)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg failed with error: {stderr.decode()}")

        # Create new AudioSample with transcoded file
        new_sample = AudioSample(
            tempfile=tempfile.NamedTemporaryFile(delete=False), metadata=sample.metadata
        )
        shutil.move(output_path, new_sample.filename)

        # Clean up original temporary file
        os.unlink(sample.filename)

        return new_sample

    except sp.CalledProcessError as e:
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise RuntimeError(f"Transcoding failed: {e.stderr.decode()}")


def copy_sample(source_file: str) -> AudioSample:
    """Copy a local audio file to a temporary location."""
    format = detect_audio_format(source_file)
    if not format:
        raise ValueError(f"Could not determine format for file: {source_file}")

    if format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported audio format: {format}")

    # Create and immediately close a new temporary file
    t = tempfile.NamedTemporaryFile(delete=False)
    t.close()

    shutil.copy(source_file, t.name)
    return AudioSample(tempfile=t, metadata={"original_format": format})


def is_url(source_url: str) -> bool:
    """Check if the source is a URL."""
    return source_url.startswith("http")


def download_sample(source_url: str) -> AudioSample:
    """Download an audio file from the internet."""
    # Extract format from URL
    format = path.splitext(source_url)[1].lower().lstrip(".")
    if format not in SUPPORTED_FORMATS:
        print(f"ERROR: unsupported audio format: {format}", file=sys.stderr)
        sys.exit(1)

    metadata = {"source_url": source_url, "original_format": format}

    with tempfile.NamedTemporaryFile(delete=False) as t:
        temp_path = t.name
        sh.wget(
            "-O",
            temp_path,
            source_url,
            _out=open("/dev/stdout", "wb"),
            _err=open("/dev/stderr", "wb"),
        )

    # Create new temporary file object that's closed but not deleted
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    shutil.move(temp_path, temp_file.name)

    return AudioSample(tempfile=temp_file, metadata=metadata)


def checksum_sample(sample: AudioSample) -> str:
    """Generate MD5 checksum for the audio file."""
    with open(sample.filename, "rb") as istream:
        return hashlib.md5(istream.read()).hexdigest()


def file_sample(language: str, checksum: str, sample: AudioSample) -> None:
    """Store the sample file in the samples directory."""
    sample_name = "{language}-{checksum}.mp3".format(
        language=language, checksum=checksum
    )
    parent_dir = path.join(SAMPLE_DIR, language)
    if not path.isdir(parent_dir):
        os.mkdir(parent_dir)

    dest_file = path.join(parent_dir, sample_name)
    sh.mv(sample.filename, dest_file)


def make_stub_record(
    language: str, checksum: str, url: str, metadata: Dict[str, Any]
) -> str:
    """Create the JSON record for the sample."""
    parent_dir = path.join(INDEX_DIR, language)
    if not path.isdir(parent_dir):
        os.mkdir(parent_dir)

    record_file = path.join(parent_dir, "{language}-{checksum}.json".format(**locals()))
    print(relative_path(record_file))

    record = TEMPLATE.copy()
    record["language"] = language
    record["checksum"] = checksum
    record["media_urls"] = [url]
    record["title"] = metadata.get("title", "")
    record["date"] = metadata.get("date", "")
    record["source_name"] = metadata.get("source_name", "")
    record["source_url"] = metadata.get("source_url", "")

    with open(record_file, "w") as ostream:
        json.dump(record, ostream, indent=2, sort_keys=True)

    return record_file


def open_in_editor(filename: str) -> None:
    """Open the record in the user's preferred editor."""
    editor = os.environ.get("EDITOR", "vim")
    p = sp.Popen([editor, filename])
    p.wait()


def relative_path(filename: str) -> str:
    """Convert filename to a relative path from current directory."""
    here = os.path.abspath(".")
    filename = os.path.abspath(filename)
    if filename.startswith(here):
        return filename[len(here) :].lstrip("/")
    return filename


if __name__ == "__main__":
    main()
