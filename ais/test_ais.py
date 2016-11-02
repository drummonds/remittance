"""Unit tests for AIS

Aim to excercise both p and remittance docu
"""
from decimal import Decimal, InvalidOperation
import numpy  as np
import os
import pandas as pd
from pandas.util.testing import assert_series_equal
from unittest import TestCase, main

from ais import p, RemittanceDoc


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
                            p(pd.Series(np.arange(0.50, 0.51, 0.005))), "Testing p works on Series")

    def test_p_other(self):
        """ Testing error handling for wrong data types
        """
        self.assertRaises(TypeError, lambda _: p(pd.DataFrame(columns=['Error'])))

    def test_RemittanceDoc(self):
        """Reading in test case and then testing some facts about it.
        """
        try:
            ais_doc = RemittanceDoc(os.getcwd() + '\\' + '16267829_609 - test.xls')
        except FileNotFoundError:
            ais_doc = RemittanceDoc(os.getcwd() + '\\ais\\' + '16267829_609 - test.xls')
        self.assertEqual(ais_doc.sum_total, Decimal('10467.92'))
        self.assertEqual(ais_doc.df['Our Ref'][1],160280459)


if __name__ == '__main__':
    main()
