# -*- coding: utf-8 -*-
#
#  audio.py
#  wide-language-index
#

"""
Audio manipulation utilities.
"""

import contextlib
import tempfile

import pydub
import sh

MS_PER_S = 1000


@contextlib.contextmanager
def cropped(mp3_file, offset, duration, adjust_volume=True):
    whole_clip = pydub.AudioSegment.from_mp3(mp3_file)
    selected = whole_clip[offset * MS_PER_S:(offset + duration) * MS_PER_S]

    with tempfile.NamedTemporaryFile(suffix='.mp3') as t:
        selected.export(t, format='mp3')

        # normalize the sample's volume
        if adjust_volume:
            sh.mp3gain('-r', '-k', '-t', '-s', 'r', t.name)

        yield t.name


def play_mp3(mp3_file):
    print('<playing...', end='', flush=True)
    p = sh.afplay(mp3_file, _bg=True)
    try:
        p.wait()
        print('done>')
    except KeyboardInterrupt:
        p.terminate()
        print('cancelled>')
        return False
