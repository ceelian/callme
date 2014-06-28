import codecs
import os
import re

import setuptools


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*'([\d.]+)'")
    init_py = os.path.join(os.path.dirname(__file__), 'callme', '__init__.py')
    with open(init_py) as fp:
        for line in fp:
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
        else:
            raise RuntimeError('Cannot find version in callme/__init__.py')


setuptools.setup(
    name="callme",
    version=read_version(),
    packages=setuptools.find_packages(),
    install_requires=['kombu>=3.0.0'],

    # metadata for upload to PyPI
    author="Christian Haintz",
    author_email="christian.haintz@orangelabs.at",
    description="Python AMQP RPC module",
    long_description=codecs.open("doc/source/introduction.rst", "r",
                                 "utf-8").read(),
    keywords="amqp rpc",
    platforms=["any"],
    url="http://packages.python.org/callme",
    license='BSD',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Developers",
        "Topic :: System :: Networking",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    zip_safe=True,
)
