#
#  Makefile
#

default: help

help:
	@echo
	@echo 'Commands for working with audio samples'
	@echo
	@echo '  make audit    check that annotations are all valid'
	@echo

audit:
	python src/audit.py
