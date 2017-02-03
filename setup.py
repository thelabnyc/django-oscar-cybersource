#!/usr/bin/env python
from setuptools import setup, find_packages, Distribution
import codecs
import os.path

# Make sure versiontag exists before going any further
Distribution().fetch_build_eggs('versiontag>=1.2.0')

from versiontag import get_version, cache_git_tag  # NOQA


packages = find_packages()

install_requires = [
    'django-oscar-api-checkout>=0.2.4',
    'django-oscar-api>=1.0.10post1',
    'django-oscar>=1.3',
    'djangorestframework>=3.1.0,<3.5.0',
    'lxml>=3.7.2',
]

extras_require = {
    'development': [
        'beautifulsoup4>=4.5.3',
        'flake8>=3.2.1',
        'psycopg2>=2.6.2',
        'PyYAML>=3.12',
        'requests>=2.13.0',
    ],
}


def fpath(name):
    return os.path.join(os.path.dirname(__file__), name)


def read(fname):
    return codecs.open(fpath(fname), encoding='utf-8').read()


cache_git_tag()

setup(
    name='django-oscar-cybersource',
    description="Integration between django-oscar and the Cybersource Secure Acceptance.",
    version=get_version(pypi=True),
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: Unix',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    author='Craig Weber',
    author_email='crgwbr@gmail.com',
    url='https://gitlab.com/thelabnyc/django-oscar-cybersource',
    license='ISC',
    packages=packages,
    install_requires=install_requires,
    extras_require=extras_require,
)
