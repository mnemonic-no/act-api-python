#!/usr/bin/env sh

python3 setup.py sdist
twine upload dist/*
rm dist/*tar.gz
