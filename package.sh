#!/usr/bin/env sh

tar cvzf python-act.tgz -C .. python-act/LICENSE python-act/AUTHORS python-act/README.md python-act/setup.py python-act/act/base.py python-act/act/helpers.py python-act/act/obj.py python-act/act/utils.py python-act/act/fact.py  python-act/act/__init__.py python-act/act/schema.py
echo "Created archive file ./python-act.tgz"
