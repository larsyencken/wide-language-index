# -*- coding: utf-8 -*-
#
#  recode_language.py
#  wide-language-index
#

"""
Decide that all samples of one language code actually belong to another.
"""

import json
import pathlib
import shutil

import click

import mirror


@click.command()
@click.argument("from_code")
@click.argument("to_code")
def main(from_code, to_code):
    "Recode one language code to another."
    move_records(from_code, to_code)
    move_audio(from_code, to_code)
    remirror_files(from_code, to_code)


def move_records(from_code, to_code):
    index = pathlib.Path("index")
    source = index / from_code
    dest = index / to_code

    source_files = list(source.glob("*.json"))

    print("Re-indexing {0} records...".format(len(source_files)))

    if not dest.is_dir():
        dest.mkdir()

    for source_file in source_files:
        with open(source_file.as_posix()) as istream:
            record = json.load(istream)

        assert record["language"] == from_code
        record["language"] = to_code

        dest_file = dest / "{language}-{checksum}.json".format(**record)
        with open(dest_file.as_posix(), "w") as ostream:
            ostream.write(json.dumps(record, indent=2, sort_keys=True))

        source_file.unlink()


def move_audio(from_code, to_code):
    samples = pathlib.Path("samples")
    source = samples / from_code
    dest = samples / to_code

    to_move = list(source.glob("*.mp3"))
    print("Moving {0} audio files...".format(len(to_move)))

    if not dest.is_dir():
        dest.mkdir()

    for source_file in to_move:
        checksum = source_file.name.split(".")[0].split("-")[1]
        dest_file = dest / "{0}-{1}.mp3".format(to_code, checksum)
        shutil.move(source_file.as_posix(), dest_file.as_posix())


def remirror_files(from_code, to_code):
    records = [
        (f, json.load(open(f.as_posix())))
        for f in (pathlib.Path("index") / to_code).glob("*.json")
    ]

    is_bad_mirror = lambda url: (
        "/mirror." in url and "/{0}/{0}-".format(from_code) in url
    )

    to_remirror = [
        (f, r) for (f, r) in records if any(is_bad_mirror(u) for u in r["media_urls"])
    ]

    print("Remirroring {0} files...".format(len(to_remirror)))

    filenames = []
    for f, r in to_remirror:
        media_urls = [u for u in r["media_urls"] if not is_bad_mirror(u)]
        r["media_urls"] = media_urls
        with open(f.as_posix(), "w") as ostream:
            ostream.write(json.dumps(r, indent=2, sort_keys=True))

        filenames.append(f.as_posix())

    mirror.mirror_records(filenames)


if __name__ == "__main__":
    main()
