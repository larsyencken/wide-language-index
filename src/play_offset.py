#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  play_offset.py
#  wide-language-index
#

import click

import audio


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
    with audio.cropped(path, offset, duration) as clip:
        return audio.play_mp3(clip)


if __name__ == '__main__':
    play_offset_cmd()
