#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  generate_clips.py
#  wide-language-index
#

import glob
import json
import os
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple

import click

from . import audio


@click.command()
@click.option("--workers", default=None, type=int, help="Number of worker processes")
def make_clips(workers: int = None):
    """
    Generate the short clips for every good annotation in the dataset.
    Uses parallel processing to speed up clip generation.
    """
    # Collect all tasks first
    tasks = list(iter_annotations())
    total_tasks = len(tasks)
    print(f"Found {total_tasks} clips to generate")

    # Use CPU count - 1 if workers not specified to leave one core free
    if workers is None:
        workers = max(1, (os.cpu_count() or 4) - 1)

    print(f"Using {workers} worker processes")

    # Process in parallel
    completed = 0
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(make_clip, sample, annotation): (sample, annotation)
            for sample, annotation in tasks
        }

        # Track progress as futures complete
        for future in as_completed(futures):
            sample, annotation = futures[future]
            try:
                future.result()  # Check for exceptions
                completed += 1
                if completed % 10 == 0 or completed == total_tasks:
                    print(f"Progress: {completed}/{total_tasks} clips processed")
            except Exception as e:
                print(f"Error processing {sample['checksum']}: {str(e)}")


def iter_annotations() -> List[Tuple[Dict, Dict]]:
    """
    Returns list of (sample, annotation) tuples for all good annotations.
    """
    tasks = []
    for filename in glob.glob("index/*/*.json"):
        with open(filename) as istream:
            sample = json.load(istream)
            for annotation in sample.get("annotations", []):
                if annotation["label"] == "good":
                    tasks.append((sample, annotation))
    return tasks


def make_clip(sample: Dict, annotation: Dict) -> None:
    """
    Generate a single clip from the sample and annotation.
    """
    source_file = "samples/{language}/{language}-{checksum}.mp3".format(
        language=sample["language"],
        checksum=sample["checksum"],
    )

    dest_file = (
        "samples/_annotated/{language}/{language}-{checksum}-{offset}-{end}.mp3".format(
            language=sample["language"],
            checksum=sample["checksum"],
            offset=annotation["offset"],
            end=annotation["offset"] + annotation["duration"],
        )
    )

    # Skip if already exists
    if os.path.exists(dest_file):
        return

    # Ensure parent directory exists
    parent_dir = os.path.dirname(dest_file)
    os.makedirs(parent_dir, exist_ok=True)

    # Generate clip
    with audio.cropped(
        source_file, annotation["offset"], annotation["duration"]
    ) as temp_file:
        shutil.copy(temp_file, dest_file)


if __name__ == "__main__":
    make_clips()
