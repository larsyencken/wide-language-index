#
#  Makefile
#

default: help

help:
	@echo
	@echo 'Commands for working with the index'
	@echo
	@echo '  make .venv      build the sandbox required for other commands'
	@echo '  make audit      check that annotations are all valid'
	@echo '  make fetch      fetch all audio samples in the index'
	@echo '  make normalize  reformat all json records to a standard form'
	@echo '  make annotate   start an annotation session'
	@echo '  make mirror     mirror samples to s3'
	@echo '  make rss        scrape rss feeds for new audio samples'
	@echo '  make clips      make short clips for every good annotation'
	@echo

.venv: pyproject.toml uv.lock
	uv sync
	touch $@

audit: .venv
	.venv/bin/audit

fetch: .venv
	mkdir -p samples
	.venv/bin/fetch-index --prefer-mirrors

normalize: .venv
	.venv/bin/normalize

annotate: .venv
	.venv/bin/annotate --strategy greedy || :
	make stats
 
stats: .venv
	.venv/bin/annotation-stats STATS.md

mirror: .venv
	.venv/bin/mirror

rss: .venv
	.venv/bin/fetch-rss-feed

clips: fetch .venv
	mkdir -p samples/_annotated
	.venv/bin/generate-clips

prompt:
	uv tool run files-to-prompt Makefile src README.md STATS.md pyproject.toml data | pbcopy

lint: .venv
	uv run ruff check src

format: .venv normalize
	uv run ruff format src

test: lint
