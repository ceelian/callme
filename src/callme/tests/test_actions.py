#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import unittest
import callme
import sys
import copy


class ActionsTestCase(unittest.TestCase):
	
	def setUp(self):
		pass
	def tearDown(self):
		pass
	
	def test_dummy(self):
		pass
			
			
def suite():
	suite = unittest.TestSuite()
	if len(sys.argv) > 1 and sys.argv[1][:2] == 't:':
		suite.addTest(ActionsTestCase(sys.argv[1][2:]))
	else:
		suite.addTest(unittest.makeSuite(ActionsTestCase, 'test'))
	return suite


if __name__ == '__main__':
	#call it with 
	#t:<my_testcase>
	#to launch only <my_testcase> test 
	unittest.TextTestRunner(verbosity=1).run(suite())