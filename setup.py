from setuptools import setup, find_packages
import codecs
import sys
import os


sys.path.insert(0, 'src/')
init_pyc = 'src/callme/__init__.pyc'
if os.path.exists(init_pyc):
    os.remove(init_pyc)

from callme import info


if os.path.exists("doc/source/introduction.rst"):
    long_description = codecs.open('doc/source/introduction.rst',
                                   "r", "utf-8").read()
else:
    long_description = "See " + callme.__homepage__


setuptools_options = {
    'test_suite': 'callme.tests.suite',
    'zip_safe': True,
}


setup(
    name = "callme",
    version = info.__version__,
    packages = find_packages('src'),
    package_dir = {'':'src'},
    install_requires = ['kombu>=1.2.1,<3.0.0'],
  
    # metadata for upload to PyPI
    author = info.__author__,
    author_email = info.__contact__,
    description = info.__doc__,
    long_description=long_description,
    keywords="amqp rpc",
    platforms=["any"],
    url = info.__homepage__,
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
