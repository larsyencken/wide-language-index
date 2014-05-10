# languagegame-data

The audio dataset powering the Great Language Game.

## Overview

This dataset is an index of public audio samples across a wide variety of languages. For some of these samples, 20 second snippets have been annotated as being good or bad examples of the language.

If your system meets the required dependencies, building and fetching authentic examples of different languages should be as simple as running: `make`.

## Contents

### Index

The `index/` folder contains references to publicly accessible audio samples for which the principal language has been pre-determined. Each sample is represented by a JSON file containing, at minimum:

- `language`: the ISO code for the language
- `sample_url`: the URL of the raw sample file
- `source_name`: what venue or outlet published the audio file
- `title`: the title of the podcast or sample
- `date`: the date of publication of the sample

It may also contain the optional fields:

- `source_url`: the URL of the page containing the podcast, for context
- `description`: a description of the contents, in English or in the source language

The filename used for the JSON file representing a sample currently has no meaning.

### Annotations

The `annotations/` folder contains annotations on audio samples, one file per sample and offset. The JSON for an annotation mirrors that of its sample, but also must contain:

- `annotation`: `good` or `bad`
- `annotator`: who made the annotation, either a Github username or an email address
- `sample_offset`: how many seconds into the audio file the subsample starts
- `sample_length`: how long the subsample goes for, in seconds (usually 20)

## Contributing

### To the index

This is the easiest way to contribute. Find an audio sample of known language, and propose that it be added to the index. Good samples are:

- Primarily in one language
- Of a few minutes in length, no more than an hour

### To the annotations

_To be documented._ You'll need to run a script to generate unlabeled 20s snippets. You should mark a sample as `good` if, to the best of your ability to judge, it is:

- Free from music or noise
- Free from long pauses
- Entirely in the target language

Otherwise, mark it as `bad`.


Lars Yencken <lars@yencken.org>
