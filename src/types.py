# -*- coding: utf-8 -*-
#
#  types.py
#  wide-language-index
#


from characteristic import attributes, Attribute


@attributes([
    "tempfile",
    Attribute("metadata", default_factory=dict)
])
class AudioSample:
    """
    An audio sample that's ready to ingest, along with optional metadata that we
    might have depending on its source.
    """
    @property
    def filename(self):
        return self.tempfile.name
