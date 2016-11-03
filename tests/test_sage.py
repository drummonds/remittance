"""Unit tests for AIS

Aim to exercise both p and remittance docu
"""
from decimal import Decimal
from unittest import TestCase, main
from unipath import Path

from h3_yearend import p
from remittance import Sage, RemittanceDoc

BASE_DIR = Path(__file__).ancestor(2)
TEST_DIR = BASE_DIR.child('tests')


class SageTestCase(TestCase):

    def test_sage_number(self):
        sage = Sage()
        self.assertEqual('X322', sage.using_invoice_get(57735, 'Account Ref'))
        self.assertEqual(Decimal('685.70'), sage.using_invoice_get(57735, 'Net Amount'))
        self.assertEqual('X322', sage.using_invoice_get('57735', 'Account Ref'))
        self.assertEqual(Decimal('685.70'), sage.using_invoice_get('57735', 'Net Amount'))


    def test_sage_enrich(self):
        ais_doc = RemittanceDoc(TEST_DIR.child('163167829_678.XLSX'))
        self.assertEqual(ais_doc.sum_total, p('3929.82'))
        sage = Sage()


if __name__ == '__main__':
    main()
