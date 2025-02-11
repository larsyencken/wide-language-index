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

import numpy as np
import pydub
import sh
from characteristic import Attribute, attributes
from sh import afplay, mp3gain

MS_PER_S = 1000


@contextlib.contextmanager
def cropped(mp3_file, offset, duration, adjust_volume=True):
    whole_clip = pydub.AudioSegment.from_mp3(mp3_file)
    selected = whole_clip[offset * MS_PER_S : (offset + duration) * MS_PER_S]

    if is_bad_mono(selected):
        selected = selected.set_channels(1)

    with tempfile.NamedTemporaryFile(suffix=".mp3") as t:
        selected.export(t, format="mp3")

        # normalize the sample's volume
        if adjust_volume:
            mp3gain("-r", "-k", "-t", "-s", "r", t.name)

        yield t.name


def is_bad_mono(segment):
    "Is there sound on only one channel?"
    if segment.channels != 2:
        return False

    w = segment.sample_width
    if w == 1:
        dtype = np.uint8
    elif w == 2:
        dtype = np.uint16
    else:
        raise Exception("non-standard sample width: {0}".format(w))

    a = np.fromstring(segment._data, dtype=dtype).reshape(
        (int(segment.frame_count()), segment.channels)
    )
    return (a[:, 0] == 0).mean() > 0.4 or (a[:, 1] == 0).mean() > 0.4


def play_mp3(mp3_file):
    print("<playing...", end="", flush=True)
    try:
        p = afplay(mp3_file, _bg=True, _bg_exc=False)
        p.wait()
        print("done>")
    except (KeyboardInterrupt, sh.SignalException_SIGINT):
        p.terminate()
        print("cancelled>")
        return True

    return True


@attributes(["tempfile", Attribute("metadata", default_factory=dict)])
class AudioSample:
    """
    An audio sample that's ready to ingest, along with optional metadata that we
    might have depending on its source.
    """

    @property
    def filename(self):
        return self.tempfile.name
