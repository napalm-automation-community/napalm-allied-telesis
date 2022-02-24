"""setup.py file."""

#import uuid

from setuptools import setup, find_packages

__author__ = 'Peter Rupp <Peter.Rupp@tq-group.com'

with open("requirements.txt", "r") as fs:
    reqs = [r for r in fs.read().splitlines() if (len(r) > 0 and not r.startswith("#"))]

with open("README.md", "r" ) as fh:
	long_description = fh.read()

setup(
    name="napalm-alliedtelesis",
    version="0.1.0",
    packages=find_packages(),
    author="Peter Rupp",
    author_email="Peter.Rupp@tq-group-com",
    description="Allied Telesis Driver for Napalm",
    long_description_content_type="text/markdown",
    long_description=long_description,
    classifiers=[
        'Topic :: Utilities',
         'Programming Language :: Python',
         'Programming Language :: Python :: 3',
         'Programming Language :: Python :: 3.8',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
    ],
    url="https://github.com/napalm-automation/napalm-alliedtelesis",
    include_package_data=True,
    install_requires=reqs,
)
