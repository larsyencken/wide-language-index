# wide-language-index

The Wide Language Index, a listing of publicly available samples of a large number of different languages.

## Overview

The Wide Language Index is an attempt to curate a set of examples of a wide variety of languages. For each sample. The index itself contains a listing of samples and information about them. The audio files themselves are not bundled in, but can be downloaded as needed.

If your system meets the required dependencies, fetching examples of different languages should be as simple as running: `make fetch`.

## Layout

The `index/` folder contains references to publicly accessible audio samples for which the principal language has been pre-determined. Each sample is represented by a JSON file containing, at minimum:

- `language`: the ISO 693-3 code for the language
- `media_urls`: the URL of the raw sample file
- `source_name`: what venue or outlet published the audio file
- `title`: the title of the podcast or sample
- `date`: the date of publication of the sample
- `checksum`: an md5 checksum of the language

It may also contain the optional fields:

- `source_url`: the URL of the page containing the podcast, for context
- `description`: a description of the contents, in English or in the source language

Each sample's file is named as `<language>/<language>-<checksum>.json`.

## Contributing

### To the index

This is the easiest way to contribute. Find an audio sample of known language, and propose that it be added to the index. Good samples are:

- Primarily in one language
- Of a few minutes in length, no more than an hour


Lars Yencken <lars@yencken.org>
