"""Setup script for the python-act library module"""

from os import path
from setuptools import setup

# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), "rb") as f:
    long_description = f.read().decode('utf-8')

setup(
    name="act-api",
    version="1.0.27",
    author="mnemonic AS",
    author_email="opensource@mnemonic.no",
    description="Python library to connect to the ACT rest API",
    long_description=long_description,
    long_description_content_type='text/markdown',
    license="MIT",
    keywords="ACT, mnemonic",
    url="https://github.com/mnemonic-no",
    packages=["act.api"],
    namespace_packages=['act'],
    install_requires=['requests', 'responses'],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: ISC License (ISCL)",
    ],
)
