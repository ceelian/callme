import unittest

import test_actions

def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_actions.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
