#
#  Makefile
#

ENV = /tmp/virtualenv/wide-language-index
PIP = $(ENV)/bin/pip
PY = $(ENV)/bin/python

default: help

help:
	@echo
	@echo 'Commands for working with the index'
	@echo
	@echo '  make audit    check that annotations are all valid'
	@echo '  make fetch    fetch all audio samples in the index'
	@echo

env/: requirements.pip
	test -d $(ENV) || virtualenv $(ENV)
	$(PIP) install -r requirements.pip

audit: env
	$(PY) src/audit.py

fetch: env
	mkdir -p samples
	$(PY) src/fetch_index.py index samples
