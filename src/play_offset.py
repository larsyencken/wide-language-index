#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  play_offset.py
#  wide-language-index
#

import tempfile

import click
import pydub
import sh


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.argument('offset', type=int)
@click.argument('duration', type=int)
def play_offset_cmd(path, offset, duration):
    """
    Play the given audio file at the given offset, for the specified duration.
    Offset and duration are in whole seconds.
    """
    play_offset(path, offset, duration)


def play_offset(path, offset, duration):
    """
    Play only part of the given mp3 file. Return True if the whole clip
    played.
    """
    sample = get_sample(path, offset, duration)
    return play_sample(sample)


def get_sample(path, offset, duration):
    entire_segment = pydub.AudioSegment.from_mp3(path)
    offset_ms = offset * 1000
    duration_ms = duration * 1000
    selected = entire_segment[offset_ms:offset_ms + duration_ms]
    return selected


def play_sample(sample):
    with tempfile.NamedTemporaryFile(suffix='.mp3') as t:
        sample.export(t, format='mp3')

        # normalize the sample's volume
        sh.mp3gain('-r', '-k', '-t', '-s', 'r', t.name)

        p = sh.afplay(t.name, _bg=True)
        try:
            p.wait()
        except KeyboardInterrupt:
            p.terminate()
            return False

    return True


if __name__ == '__main__':
    play_offset()
