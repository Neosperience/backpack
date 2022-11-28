.PHONY: test docs build test-release release
.DEFAULT_GOAL := build

all: build

test:
	tox -e py39

docs:
	cd docs && $(MAKE) html

build:
	 python -m build
	 twine check dist/*

test-release:
	twine upload -r testpypi --skip-existing dist/*

release:
	twine upload --skip-existing dist/*
