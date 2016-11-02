import os
import unittest

from h3_yearend import p
from vendorcentral import AmazonSalesExcelToObject


class TestAmazonSales(unittest.TestCase):

    def test_invoice_with_adjustment(self):
        # Check that a local .env has been set or that their is a production variable.
        fn = 'SLUN8-20167.xlsx'
        inv = AmazonSalesExcelToObject(fn)
        assert(inv.sum() == p(1628.70))
        fn = 'SLUN_8-20164.xlsx'
        inv = AmazonSalesExcelToObject(fn)
        inv.report()
        assert(inv.sum() == p(455.10))
