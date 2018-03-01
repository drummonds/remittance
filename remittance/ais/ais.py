"""Library for reading in AIS remittance EDI excel sheets.

It checks to make sure that sheet that has been read in actually is self consistent.  There is no difference
in the format for these documents before and after the addition of the prompt payment discount (PPD).

It doesn't cover those EDI documents where there are multiple reports on one sheet.  Where this has
happened in the past (infrequently) the remittance spreadsheet has been edited.

Available classes:

- RemittanceDoc: a dataframe.

Output properties:


Available functions:

- p: rounding function to pence (moved to h3_yearend)

"""
from decimal import Decimal, InvalidOperation
from ..utils import p
import pandas as pd
import re
from sys import exc_info


class RemittanceError(Exception):
    pass


class SubDocument():
    """Holds one document table

    The AIS excel format consists of a number of sub document tables that combine to make up a single report.
    """

    def find_last_row(self):
        """ Find last row assuming at top"""
        test_row = self.parent.parse_row + 2
        while self.parent.sheet.cell_value(test_row, 0):
            test_row=test_row+1
        return test_row - 1

    def check_first_and_last_rows_are_copies(self, first, last):
        top = self.parent.sheet.cell_value(first, 6)
        bottom = self.parent.sheet.cell_value(last, 6)
        if top != bottom or top == '':
            raise RemittanceError('Cell G{}, |{}| != {}, |{}|'.format(first, top, last, bottom))
        self.sum = p(top)

    def parse_document(self):
        """Convert document into a dataframe

        Also need to see how measure the size of the table.
        """
        try:
            self.parent.check_document_type(self.parent.parse_row)
        except RemittanceError:  # Allow a couple of extra lines eg comments etc
            try:
                self.parent.check_document_type(self.parent.parse_row + 1)
                self.parent.parse_row += 1
            except:
                self.parent.check_document_type(self.parent.parse_row + 2)  # Last chance
                self.parent.parse_row += 2
        last_row = self.find_last_row()
        self.check_first_and_last_rows_are_copies(self.parent.parse_row+1, last_row+1)
        n = last_row - self.parent.parse_row - 1
        # Note parsing the data means that numeric values are in pence
        self.df = self.parent.xl.parse(skiprows=self.parent.parse_row).head(n+1).tail(n)
        self.parent.parse_row = last_row+4

    def __init__(self, parent):
        self.parent = parent
        self.parse_document()


class AISRemittanceDoc():
    """Object for parsing AIS Remittance

        The AIS transmision summary is a remittance advice and provides a breakdown of all the invoices and
        credit notes and stop notes.

        The excel form that comes in is a header followed by a number of documents.  The last document is an
        end marker.

        Public attributes:
        -df: a pandas dataframe representing all the data.
        TODO Make specific for AIS rather than a general RemittanceDoc
    """

    def __iadd__(self, b):
        self.df = self.df.append(b.df)
        self.sum_invoices = p(self.sheet.cell_value(12,1))
        self.sum_credits = p(self.sheet.cell_value(13,1))
        self.sum_stop_notes = p(self.sheet.cell_value(14,1))
        self.sum_reverse_stop_notes = p(self.sheet.cell_value(15,1))
        self.sum_invoices += b.sum_invoices
        self.sum_credits += b.sum_credits
        self.sum_stop_notes += b.sum_stop_notes
        self.sum_reverse_stop_notes += b.sum_reverse_stop_notes
        self.sum_total += b.sum_total
        return self

    def parse_title(self):
        self.title = self.sheet.cell_value(2,1)
        regex = re.compile('(\d+).+?(\d+)', re.VERBOSE)
        match = regex.search(self.title)
        try:
            g = match.groups()
            self.week = g[0]
            self.year = g[1]
        except AttributeError:
            raise RemittanceError('Parse title found no match')

    def parse_summary(self):
        self.sum_invoices = p(self.sheet.cell_value(12,1))
        self.sum_credits = p(self.sheet.cell_value(13,1))
        self.sum_stop_notes = p(self.sheet.cell_value(14,1))
        self.sum_reverse_stop_notes = p(self.sheet.cell_value(15,1))
        self.sum_total = p(self.sheet.cell_value(16,1))
        if self.sum_total != (self.sum_invoices+self.sum_credits+self.sum_stop_notes+self.sum_reverse_stop_notes):
            raise RemittanceError('Summary total doesn''t add up. \n {}'.format(self))

    def check_document_cell(self, row, col, target):
        """Check a cell contains a value and raise error if no"""
        check = self.sheet.cell_value(row, col)
        cell_ref = '{}{}'.format(chr(ord('A')+col), row+1)
        # print('Checking {} for |{}|, = |{}|'.format(cell_ref, check, target))
        if check != target:
            raise RemittanceError('Cell {} = {} is not {}'.format(cell_ref, check, target))

    def is_end_document(self):
        """Check for last document"""
        try:
            self.check_document_cell(self.parse_row+3, 1, '---- END OF REPORT ----')
            return True
        except RemittanceError:
            return False

    def check_document_type(self, row):
        """Check for Document type"""
        self.check_document_cell(row, 0, 'Document Type')

    def check_summary_and_documents(self):
        """Make sure summary agrees with sum of documents"""
        sum = 0
        for sd in self.sub_documents:
            sum += sd.sum
        if sum != self.sum_total:
            raise RemittanceError('Document sum {} not equal to summary at top {}'.format(sum, self.sum_total))

    def check(self):
        """check that cell B6 has the correct address.  The address changed on 2017-03-31 from address 1 to address2.
        Raises an error if check is not successful.
        """
        value = self.sheet.cell_value(5,1)
        address1 = 'RANKIN HOUSE'
        address2 = 'SLUMBERFLEECE LTD'
        possible_addresses = (address1, address2)
        if value not in (possible_addresses):
            raise RemittanceError('Cell B6 = {} is not in {}'.format(value, possible_addresses))


    def __init__(self, filename):
        """
        Args:
        :param filename: The complete filename of the Excel sheet that is to be parsed.
        :return: The AIS remittance document.
        """

        def check_due():
            # TODO integrate with parser so that knows about type of line
            def check_item(row):
                value = p(row['Value'])
                discount = p(row['Discount'])
                due = p(row['Due'])
                if (due != value - discount) and (row['Document Type'] != 'Rejected'):
                    print('Problem with row ({},{} due != value - discount, {},{},{}'.format(row['Document Type'],
                                                                                             row['Your Ref'],
                                                                                             due, value, discount))
                    self.checked = False

            self.df.apply(check_item, axis = 1)

        def check_df_series_add_up():
            col_total = p(self.df['Due'].sum())
            total = p(self.sum_total)
            self.checked = col_total == total

        self.xl = pd.ExcelFile(filename)
        self.sheet = self.xl.book.sheet_by_name('Sheet1')
        self.parse_title()
        self.check()
        self.parse_summary()
        self.parse_row = 18
        max_docs = 10
        self.sub_documents = []
        while not self.is_end_document():
            self.sub_documents.append(SubDocument(self))
            max_docs -= 1
            if max_docs < 0:
                raise RemittanceError('Too many documents, probably an error')
        self.check_summary_and_documents()
        self.df = self.sub_documents[0].df
        for i,d in enumerate(self.sub_documents):
            if i > 0:
                self.df=self.df.append(d.df, ignore_index=False)
        check_due()
        check_df_series_add_up()
        self.checked = True # raises an error if not

    def __str__(self):
        try:
            s = 'Title = {}\n'.format(self.title)
            s += 'Week {}, Year {}\n'.format(self.week, self.year)
            s += 'Invoices {}, credits {}, stop_notes {}, reversal stop notes {}, total {}\n'.format(
                self.sum_invoices, self.sum_credits, self.sum_stop_notes, self.sum_reverse_stop_notes, self.sum_total)
        except AttributeError:
            s = '#Some problem'
        return s
