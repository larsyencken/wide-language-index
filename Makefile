#
#  Makefile
#

PY = uv run

default: help

help:
	@echo
	@echo 'Commands for working with the index'
	@echo
	@echo '  make .env        build the sandbox required for other commands'
	@echo '  make audit      check that annotations are all valid'
	@echo '  make fetch      fetch all audio samples in the index'
	@echo '  make normalize  reformat all json records to a standard form'
	@echo '  make annotate   start an annotation session'
	@echo '  make mirror     mirror samples to s3'
	@echo '  make rss        scrape rss feeds for new audio samples'
	@echo '  make clips      make short clips for every good annotation'
	@echo

.env: pyproject.toml uv.lock
	uv sync
	touch $@

audit: .env
	$(PY) src/audit.py

fetch: .env
	mkdir -p samples
	$(PY) src/fetch_index.py --prefer-mirrors

normalize: .env
	$(PY) src/normalize.py

annotate: .env
	$(PY) src/annotate.py || :
	make stats

stats: .env
	$(PY) src/annotation_stats.py STATS.md

mirror: .env
	$(PY) src/mirror.py

rss: .env
	$(PY) src/fetch_rss_feed.py

clips: fetch .env
	mkdir -p samples/_annotated
	$(PY) src/generate_clips.py
