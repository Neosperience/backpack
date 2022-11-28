.PHONY: test docs build test-release release
.DEFAULT_GOAL := help

# --------- Help script ---------

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:			## Show this help message
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

test:			## Test the library with tox
	tox -e py39

docs:			## Generate documentation
	cd docs && $(MAKE) html

build:			## Build the library for distribution
	 python -m build
	 twine check dist/*

test-release:	## Release the library on test pypi
	twine upload -r testpypi --skip-existing dist/*

release:		## Release the library on pypi
	twine upload --skip-existing dist/*
