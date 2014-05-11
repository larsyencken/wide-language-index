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

audit:
	python src/audit.py

fetch:
	mkdir -p samples
	python src/fetch_index.py index samples
