"""Unit tests for AIS

Aim to exercise both p and remittance docu
"""
import datetime as dt
from decimal import Decimal
from unittest import TestCase, main
from unipath import Path

from h3_yearend import p
from remittance import Sage, RemittanceDoc, Remittance, ParseItems

BASE_DIR = Path(__file__).ancestor(2)
TEST_DIR = BASE_DIR.child('tests')


class SageTestCase(TestCase):

    def test_sage_number(self):
        sage = Sage()
        self.assertEqual('X322', sage.using_invoice_get(57735, 'ACCOUNT_REF'))
        self.assertEqual(Decimal('685.70'), p(sage.using_invoice_get(57735, 'NET_AMOUNT')))
        self.assertEqual('X322', sage.using_invoice_get('57735', 'ACCOUNT_REF'))
        self.assertEqual(Decimal('685.70'), p(sage.using_invoice_get('57735', 'NET_AMOUNT')))


    def test_sage_enrich(self):
        ais_doc = RemittanceDoc(TEST_DIR.child('163167829_678.XLSX'))
        ais_doc.payment_date = dt.datetime(2016, 8, 31)
        self.assertEqual(ais_doc.sum_total, p('3929.82'))
        sage = Sage()
        sage.enrich_remittance_doc(ais_doc)
        assert ais_doc.checked
        ais = Remittance()
        pli = ParseItems(ais_doc, ais)


if __name__ == '__main__':
    main()
