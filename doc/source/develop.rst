================================================================
Development of callme
================================================================

Developement of Callme happens on Github https://github.com/ceelian/callme.
Feel free to contribute.

Preparing packaging and distribution
------------------------------------

Test everything
+++++++++++++++
	
in the shell::
		
	cd src/callme/tests
	python test_actions.py
	
	
Change Version
++++++++++++++

Change the version in ``src/callme/__init__.py``
Add changelog in ``CHANGELOG`` 
	
	
Commit and Tag
++++++++++++++
	
in the shell::
	
	#clean stuff
	cd doc
	make clean

	python setup.py clean
	
	# tag, commit and push to github
	git commit -a
	git push
	git tag -a vX.X.X
	git push --tags
	
	# upload to pypi
	python setup.py sdist upload
	
	# make doc and upload
	cd doc
	make html
	
	python setup.py upload_sphinx
	