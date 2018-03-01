"""Unit tests for AIS

Aim to excercise both p and remittance docu
"""
from decimal import Decimal, InvalidOperation
import numpy  as np
import os
import pandas as pd
from pandas.util.testing import assert_series_equal
from unittest import TestCase, main
from unipath import Path

from remittance import AISRemittanceDoc, RemittanceError, p

BASE_DIR = Path(__file__).ancestor(2)
TEST_DIR = BASE_DIR.child('tests')

class AISTestCase(TestCase):
    def test_p_zero(self):
        """Test the zero cases
        """
        self.assertEqual(Decimal('0'), p(0.0))
        self.assertEqual(Decimal('0'), p(0))

    def test_p_positive(self):
        """Test rounding positive numbers
        """
        self.assertEqual(Decimal('0.49'), p(0.49))
        self.assertEqual(Decimal('0.49'), p(0.494))
        self.assertEqual(Decimal('0.49'), p(0.494))
        self.assertEqual(Decimal('0.50'), p(0.495))

    def test_p_negative(self):
        """Test rounding negative numbers
        """
        self.assertEqual(Decimal('-0.49'), p(-0.49))
        self.assertEqual(Decimal('-0.49'), p(-0.494))
        # Test series,

    def test_p_series(self):
        """ Testing ability to iterate over a series of data
        """
        assert_series_equal(pd.Series([Decimal('0.50'), Decimal('0.51'), Decimal('0.51')]),
                            pd.Series(p(pd.Series(np.arange(0.50, 0.51, 0.005)))), "Testing p works on Series")

    def test_p_other(self):
        """ Testing error handling for wrong data types
        """
        self.assertRaises(TypeError, lambda _: p(pd.DataFrame(columns=['Error'])))

    def test_RemittanceDoc(self):
        """Reading in test case and then testing some facts about it.
        """
        ais_doc = AISRemittanceDoc(TEST_DIR.child('16267829_609 - test.xls'))
        self.assertEqual(ais_doc.sum_total, Decimal('10467.92'))
        self.assertEqual(ais_doc.df['Our Ref'][1],160280459)

    def test_RemittanceDoc2(self):
        ais_doc = AISRemittanceDoc(TEST_DIR.child('163167829_678.XLSX'))
        self.assertEqual(ais_doc.sum_total, p('3929.82'))
        self.assertEqual(len(ais_doc.df), 10)
        self.assertTrue(ais_doc.checked)
        ais_doc += ais_doc
        self.assertEqual(ais_doc.sum_total, p('7859.64'))
        # Problems with addition This only works in a very specific case.  RemittanceDoc depends on totals
        # which are specified in the original document so you cannot easily add two together
        # ais_doc2 = ais_doc + ais_doc
        # self.assertEqual(ais_doc2.sum_total, p('7859.64'))
        # self.assertEqual(ais_doc.sum_total, p('3929.82'))

    def test_RemittanceFail(self):
        self.assertRaises(RemittanceError, AISRemittanceDoc, TEST_DIR.child('163167829_678a.XLSX'))

    def test_RemittanceDoc3(self):
        """ Cenpac started adding addition comments at top of header so make sure actually can still parse.
        Added a little flexibility for an extre couple of lines before complaining.
        There seems to have been a bit of a gap.  Maybe someone complained."""
        ais_doc = AISRemittanceDoc(TEST_DIR.child('163967829_686.XLSX'))
        self.assertEqual(ais_doc.sum_total, p(34348.58))
        self.assertTrue(ais_doc.checked)


if __name__ == '__main__':
    main()
