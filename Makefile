#
#  Makefile
#

default: help

help:
	@echo
	@echo 'Commands for working with the index'
	@echo
	@echo '  make audit    check that annotations are all valid'
	@echo '  make fetch    fetch all audio samples in the index'
	@echo

env/: requirements.pip
	virtualenv env
	env/bin/pip install -r requirements.pip

audit: env
	env/bin/python src/audit.py

fetch: env
	mkdir -p samples
	env/bin/python src/fetch_index.py index samples
