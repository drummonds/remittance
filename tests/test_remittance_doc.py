"""Unit tests for Remittance Doc

Aim to excercise RemittanceDoc
"""
from unittest import TestCase, main

from remittance import RemittanceDoc

class RemittanceDocTestCase(TestCase):
    def test_creation(self):
        doc = RemittanceDoc()

