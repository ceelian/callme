from setuptools import setup, find_packages
from distutils.cmd import Command
import codecs
import sys, os
import doctest
from glob import glob

sys.path.insert(0,'src/')
init_pyc = 'src/callme/__init__.pyc'
if os.path.exists(init_pyc):
    os.remove(init_pyc)

import callme


if os.path.exists("doc/source/introduction.rst"):
    long_description = codecs.open('doc/source/introduction.rst', "r", "utf-8").read()
else:
    long_description = "See " + callme.__homepage__


setuptools_options = {
	'test_suite': 'callme.tests.suite',
	'zip_safe': True,
}

setup(
    name = "callme",
    version = callme.__version__,
    packages = find_packages('src'),
    package_dir = {'':'src'},
    install_requires = ['kombu>=1.2.1'],
  
    # metadata for upload to PyPI
    author = callme.__author__,
    author_email = callme.__contact__,
    description = callme.__doc__,
    long_description=long_description,
    keywords = "amqp rpc",
    platforms=["any"],
    url = callme.__homepage__,
    license = 'BSD',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Developers",
        "Topic :: System :: Networking",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    **setuptools_options

 

)

