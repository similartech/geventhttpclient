script_dir=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

SIMILARTECH_PYTHON_ROOT=${script_dir}/..
VENV=${SIMILARTECH_PYTHON_ROOT}/venv/bin/
PYTHON=python2.7
VENV_PYTHON=${VENV}python

build_ext:
	python setup.py build_ext --inplace

test:
	$(VENV_PYTHON) -m pytest src/geventhttpclient/tests

_develop:
	python setup.py develop

develop: _develop build_ext

clean:
	rm -rf build
	find . -name '*.pyc' -delete

dist:
	python setup.py sdist upload

release:
	cat release.md

.PHONY: develop
