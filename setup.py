#!/usr/bin/env python
from setuptools import setup, find_packages, Distribution
import codecs
import os.path

# Make sure versiontag exists before going any further
Distribution().fetch_build_eggs('versiontag>=1.2.0')

from versiontag import get_version, cache_git_tag  # NOQA


packages = find_packages('src')

install_requires = [
    'django-fernet-fields>=0.5',
    'django-oscar-api-checkout>=0.5.0b2',
    'django-oscar-api>=1.3.0',
    'django-oscar>=1.5',
    'lxml>=4.1.1',
    'phonenumbers>=8.8.8',
    'python-dateutil>=2.8.0',
]

extras_require = {
    'development': [
        'beautifulsoup4>=4.6.0',
        'coverage>=4.4.2',
        'flake8>=3.5.0',
        'psycopg2cffi>=2.7.7',
        'PyYAML>=3.12',
        'requests>=2.18.4',
        'sphinx>=1.5.2',
        'sphinx-rtd-theme>=0.4.3',
        'tox>=2.6.0',
        'versiontag>=1.2.0',
        'suds-jurko==0.6',
        'instrumented-soap==1.1.1',
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
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    author='Craig Weber',
    author_email='crgwbr@gmail.com',
    url='https://gitlab.com/thelabnyc/django-oscar-cybersource',
    license='ISC',
    package_dir={'': 'src'},
    packages=packages,
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
)
