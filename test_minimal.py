import unittest
import sys

class MinimalTest(unittest.TestCase):
    def test_simple(self):
        print("Running simple test")
        self.assertTrue(True)

if __name__ == '__main__':
    print("Starting test run")
    unittest.main(verbosity=2)
