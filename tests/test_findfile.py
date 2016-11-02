import os
import unittest

from vendorcentral import amazon_find_one_file


class TestFindOneFile(unittest.TestCase):

    def test_find_one_file(self):
        # Check that a local .env has been set or that their is a production variable.
        fn = amazon_find_one_file()
        assert fn == 'SLUN8-20167.xlsx'
