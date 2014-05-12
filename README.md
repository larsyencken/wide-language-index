# wide-language-index

A listing of publicly available audio samples of a large number of different languages.

## Overview

The Wide Language Index is an attempt to curate a set of examples of a wide variety of languages from public podcasts. The index itself contains a listing of samples and information about them. The audio files themselves are not bundled in, but can be downloaded as needed.

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

Find an audio sample in a known language, and propose that it be added to the index. Good samples are:

- Primarily in one language
- Of a few minutes in length, no more than an hour
- In a language that doesn't yet have much coverage

If you're tech-savvy, feel free to open a pull request with the proposed JSON entry for the sample. If you're not, just [open an issue](https://github.com/larsyencken/wide-language-index/issues) with a link to the page for the sample, making sure to identify its language.


Lars Yencken <lars@yencken.org>
