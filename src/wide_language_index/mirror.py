#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  mirror.py
#  wide-language-index
#

from __future__ import absolute_import, division, print_function

import glob
import hashlib
import json
import os
import sys
from os import getenv, path
from typing import Any, Dict, List

import boto3
import click
from dotenv import load_dotenv

BUCKET = "mirror.widelanguageindex.org"
REQUIRED_ENV_VARS = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_ENDPOINT_URL"]


def validate_environment() -> None:
    """
    Validate that all required environment variables are set.
    Raises RuntimeError if any are missing.
    """
    load_dotenv()

    missing = [var for var in REQUIRED_ENV_VARS if not getenv(var)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables:\n"
            f"  {', '.join(missing)}\n"
            "Please ensure these are set in your .env file"
        )


def get_s3_client():
    """
    Create an S3 client using credentials from environment variables.
    """
    return boto3.client(
        "s3",
        aws_access_key_id=getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=getenv("AWS_SECRET_ACCESS_KEY"),
        endpoint_url=getenv("AWS_ENDPOINT_URL"),
    )


@click.command()
@click.option("--language", help="Only mirror the given language.")
@click.option("--only", help="Only mirror the specified record file.")
def main(language: str | None = None, only: str | None = None) -> None:
    """
    Mirror samples to Amazon S3, in case the original publisher takes them
    down. Add the mirror URL as a secondary mirror in the index record.
    """
    try:
        validate_environment()
        mirror(language=language, only=only)
    except RuntimeError as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {str(e)}", file=sys.stderr)
        sys.exit(1)


def mirror(language: str | None = None, only: str | None = None) -> None:
    s3 = get_s3_client()

    print("Scanning records...")
    queue = queue_records(language=language, only=only)

    print(f"{len(queue)} samples to be mirrored")
    for i, record in enumerate(queue):
        print(f"[{i + 1}/{len(queue)}] ", end="")
        mirror_sample(record, s3)
        save_record(record)


def mirror_records(filenames: List[str]) -> None:
    validate_environment()
    s3 = get_s3_client()
    queue = list(map(load_record, filenames))

    print(f"{len(queue)} samples to be mirrored")
    for i, record in enumerate(queue):
        print(f"[{i + 1}/{len(queue)}] ", end="")
        mirror_sample(record, s3)
        save_record(record)


def queue_records(
    language: str | None = None, only: str | None = None
) -> List[Dict[str, Any]]:
    if only:
        queue = [load_record(only)]
    else:
        queue = all_samples(language=language)

    return [s for s in queue if not sample_is_mirrored(s)]


def all_samples(language: str | None = None) -> List[Dict[str, Any]]:
    if language is not None:
        pattern = f"index/{language}/*.json"
    else:
        pattern = "index/*/*.json"

    return [load_record(f) for f in sorted(glob.glob(pattern))]


def load_record(f: str) -> Dict[str, Any]:
    with open(f) as istream:
        return json.load(istream)


def sample_is_mirrored(record: Dict[str, Any]) -> bool:
    return any(BUCKET in url for url in record["media_urls"])


def mirror_sample(record: Dict[str, Any], s3: Any) -> None:
    name = f"{record['language']}/{record['language']}-{record['checksum']}.mp3"

    filename = f"samples/{name}"
    if not path.exists(filename):
        bail('missing file {0}, did you run "make fetch"?'.format(filename))

    size = file_size(filename)
    print(f"{name} ({size})")

    checksum = md5_checksum(filename)
    if checksum != record["checksum"]:
        bail(f"invalid checksum for file {filename}")

    # Upload file with cache headers and public read access
    try:
        with open(filename, "rb") as data:
            s3.put_object(
                Bucket=BUCKET,
                Key=name,
                Body=data,
                CacheControl="max-age=157680000",  # 5 years in seconds
                ACL="public-read",
            )
    except Exception as e:
        bail(f"Failed to upload to S3: {str(e)}")

    record["media_urls"].append(f"http://{BUCKET}/{name}")


def save_record(record: Dict[str, Any]) -> None:
    filename = (
        f"index/{record['language']}/{record['language']}-{record['checksum']}.json"
    )

    s = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False)
    with open(filename, "w") as ostream:
        ostream.write(s)


def md5_checksum(filename: str) -> str:
    with open(filename, "rb") as istream:
        return hashlib.md5(istream.read()).hexdigest()


def bail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def file_size(filename: str) -> str:
    return "%.01fM" % (os.stat(filename).st_size / 2**20)


def unmirror(suffix: str) -> None:
    validate_environment()
    print(f"Deleting s3://{BUCKET}/{suffix}")
    s3 = get_s3_client()
    try:
        s3.delete_object(Bucket=BUCKET, Key=suffix)
    except Exception as e:
        bail(f"Failed to delete from S3: {str(e)}")


if __name__ == "__main__":
    main()
