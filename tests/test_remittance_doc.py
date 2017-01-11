"""Unit tests for Remittance Doc

Aim to excercise RemittanceDoc
"""
from unittest import TestCase, main

from remittance import RemittanceDoc

class RemittanceDocTestCase(TestCase):
    def test_creation(self):
        doc = RemittanceDoc()

    def test_pages(self):
        doc = RemittanceDoc()
        assert doc.numpages == 0
        assert str(doc) ==  '#No pages assigned yet'
        text = 'Hello\nWorld'
        doc.append_page(text)
        assert doc.numpages == 1
        assert str(doc) ==  '#Pages\nHello\nWorld\n'
        assert doc.pages[0][1] == 'World'
        assert doc.page[1] == 'World'
        doc.append_page(text)
        assert doc.numpages == 2
        print('|'+str(doc)+'|')
        assert str(doc) ==  '#Pages\nHello\nWorld\nHello\nWorld\n'
        assert doc.pages[1][1] == 'World'


