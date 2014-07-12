================================================================
Development of callme
================================================================
Development of Callme happens on Github https://github.com/ceelian/callme.
Feel free to contribute.

Preparing packaging and distribution
------------------------------------

Test everything
+++++++++++++++
In the shell::

    # make sure the tox package is installed
    pip install tox

    # run all tests (make sure the rabbitmq-server service is running)
    ./run_tests.sh


Change Version
++++++++++++++
Change the version in ``callme/__init__.py``.
Add changelog in ``CHANGELOG``.


Commit and Tag
++++++++++++++

Prerequisites for this is with pip (syspip):
  * sphinx
  * Sphinx-PyPI-upload

In the shell::

    # clean stuff
    cd doc
    make clean

    python setup.py clean

    # tag, commit and push to github
    git commit -a
    git push
    git tag -a vX.X.X
    git push --tags

    # first time you need to register the package
    python setup.py register

    # upload to pypi
    python setup.py sdist upload

    # make doc and upload
    cd doc
    make html

    python setup.py upload_sphinx
