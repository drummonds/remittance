"""Unit tests for AIS

Aim to exercise both p and remittance docu
"""
import datetime as dt
from decimal import Decimal
import logging
import os
import time
from unittest import TestCase, main
from unipath import Path

from dotenv import load_dotenv, find_dotenv

from h3_yearend import p
from pysage50 import Sage
from remittance import RemittanceDoc, Remittance, ParseItems, SageImportFile


BASE_DIR = Path(__file__).ancestor(2)
TEST_DIR = BASE_DIR.child('tests')


def today_as_string():
    now = dt.datetime.now()
    return dt.datetime.strftime(now, '%Y-%m-%d')

class SageTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(SageTestCase, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger('SageTestCase')

    def setUp(self):
        load_dotenv(find_dotenv())

    def cleanup(self):
        fn =TEST_DIR.child(today_as_string() + ' Remittance_AIS Import.csv')
        try:
            os.remove(fn)
        except FileNotFoundError:
            self.logger.info('Remittance file not found |{}|'.format(fn))
            pass  # failed before file was created.  Will leave one file per day
        # fn = 'tests/' + today_as_string() + ' Remittance Import.csv'

    def test_sage_number(self):
        sage = Sage()
        self.assertEqual('1100', sage.using_reference_get(57735, 'ACCOUNT_REF'))
        self.assertEqual('X322', sage.using_reference_get(57735, 'ALT_REF'))
        self.assertEqual(Decimal('685.70'), p(sage.using_reference_get(57735, 'NET_AMOUNT')))
        self.assertEqual('X322', sage.using_reference_get('57735', 'ALT_REF'))
        self.assertEqual(Decimal('685.70'), p(sage.using_reference_get('57735', 'NET_AMOUNT')))

    def test_sage_enrich(self):
        self.cleanup()
        # Check that a local .env has been set or that their is a production variable.
        ais_doc = RemittanceDoc(TEST_DIR.child('163167829_678.XLSX'))
        ais_doc.payment_date = dt.datetime.now()
        self.assertEqual(ais_doc.sum_total, p('3929.82'))
        sage = Sage()
        sage.enrich_remittance_doc(ais_doc)
        assert ais_doc.checked
        ais = Remittance()
        pli = ParseItems(ais_doc, ais)
        sif = SageImportFile(ais, sage.sqldata, 'Remittance_' + ais.supplier, file_dir=TEST_DIR)
        fn = sif.si.filename
        if False:  # Production run tidies up afterwards and makes sure all can't run twice
            time.sleep(0.5)
            from shutil import move
            path = os.getcwd() + '\\'
            move(path + '\\' + fn, path + '\\Archive\\' + fn)
            self.logger.info('Done')


if __name__ == '__main__':
    main()
