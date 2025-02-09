# -*- coding: utf-8 -*-
#
#  recode_sample.py
#  wide-language-index
#

"""
Decide that one sample actually is of another language.
"""

import json
import pathlib
import shutil
import sys

import click

import mirror


@click.command()
@click.argument("sample_file")
@click.argument("to_code")
def main(sample_file, to_code):
    "Recode one sample from one language to another."
    old_record = load_record(sample_file)
    new_record = recode_record(old_record, to_code)
    move_record(old_record, new_record)
    move_audio(old_record, new_record)
    upload_to_mirror(new_record)


def load_record(filename):
    with open(filename) as istream:
        return json.load(istream)


def recode_record(old_record, to_code):
    if old_record["language"] == to_code:
        print("ERROR: language is already {}".format(to_code))
        sys.exit(1)

    new_record = old_record.copy()
    new_record["language"] = to_code

    new_record["media_urls"] = recode_mirrors(
        old_record["media_urls"], old_record["language"], to_code
    )

    return new_record


def recode_mirrors(mirrors, from_code, to_code):
    return [m for m in mirrors if "mirror.widelanguageindex.org" not in m]


def move_record(old_record, new_record):
    source_file = record_to_path(old_record)
    dest_file = record_to_path(new_record)
    print("{} -> {}".format(source_file, dest_file))

    if not dest_file.parent.is_dir():
        dest_file.parent.mkdir()

    save_record(dest_file.as_posix(), new_record)
    source_file.unlink()


def save_record(filename, record):
    with open(filename, "w") as ostream:
        ostream.write(json.dumps(record, indent=2, sort_keys=True))


def record_to_path(r):
    l = r["language"]
    c = r["checksum"]
    return pathlib.Path("index") / l / "{}-{}.json".format(l, c)


def move_audio(old_record, new_record):
    source_file = record_to_sample(old_record)
    dest_file = record_to_sample(new_record)
    print("{} -> {}".format(source_file, dest_file))

    if not dest_file.parent.is_dir():
        dest_file.parent.mkdir()

    shutil.move(source_file.as_posix(), dest_file.as_posix())


def record_to_sample(r):
    samples = pathlib.Path("samples")
    return samples / "{language}/{language}-{checksum}.mp3".format(**r)


def upload_to_mirror(new_record):
    to_mirror = [record_to_path(new_record).as_posix()]
    mirror.mirror_records(to_mirror)


if __name__ == "__main__":
    main()
