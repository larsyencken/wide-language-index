#
#  Makefile
#

ENV = env
PIP = $(ENV)/bin/pip
PY = $(ENV)/bin/python

default: help

help:
	@echo
	@echo 'Commands for working with the index'
	@echo
	@echo '  make env        build the sandbox required for other commands'
	@echo '  make audit      check that annotations are all valid'
	@echo '  make fetch      fetch all audio samples in the index'
	@echo '  make normalize  reformat all json records to a standard form'
	@echo '  make annotate   start an annotation session'
	@echo '  make mirror     mirror samples to s3'
	@echo '  make rss        scrape rss feeds for new audio samples'
	@echo

env/: requirements.pip
	test -d $(ENV) || virtualenv $(ENV)
	$(PIP) install -r requirements.pip

audit:
	$(PY) src/audit.py

fetch:
	mkdir -p samples
	$(PY) src/fetch_index.py

normalize:
	$(PY) src/normalize.py

annotate:
	$(PY) src/annotate.py

stats:
	$(PY) src/annotation_stats.py STATS.md

mirror:
	$(PY) src/mirror.py

rss:
	$(PY) src/fetch_rss_feed.py
