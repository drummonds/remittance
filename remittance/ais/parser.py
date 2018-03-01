import math


from .ais import RemittanceError

from ..remittance import AIS_PPD_CreditNote, AISCreditNote, AgentInvoice, AIS_PPD_Invoice
from ..debit_note import DebitNote, DebitNoteReversal
from ..ais_invoice import AISInvoice
from ..utils import p

# TODO convert print statements to error logging
class ParseError(Exception):
    pass


def dummy_manual_correction(item, row):
    pass

class ParseItems:
    """This is specific to AIS.  It parses the data in the Excel sheet"""

    def check_row(self, item, row):
        """Check all the calculated values against the raw data to see if it all agrees"""
        result = True

        def check_item(prop, series, allow_rounding=False, correct_rounding=False):
            try:
                a = getattr(item, prop)
                b = p(row[series])
                if not allow_rounding:
                    if (a != b):
                        if not (a.is_nan() and b.is_nan()):
                            raise ParseError(
                                "For invoice {}, Property {} != series {}, values {},{}, types {},{}".format(
                                    row['Your Ref'], prop, series, a, b, type(a), type(b)))
                else:  # Allow rounding
                    if not (a.is_nan() and b.is_nan()):
                        if abs(a - b) > 0.01:
                            raise ParseError(
                                "For invoice {}, Property {} != series {}, values {},{}, types {},{}".format(
                                    row['Your Ref'], prop, series, a, b, type(a), type(b)))
                        elif (a != b) and correct_rounding:
                            if prop == 'vat':
                                item.correct_vat_rounding_error(p(row[series]))
                            else:
                                setattr(item, prop, p(row[series]))
            except AttributeError:
                raise (ParseError("Item {} doesn't have property {} and should have.".format(row['Your Ref'], prop)))

        check_item('net_amount', 'Sage_Net_Amount')
        check_item('vat', 'Sage_VAT_Amount', False, False)  # Thought had a problem but not sure
        check_item('gross_amount', 'Sage_Gross_Amount')
        check_item('discount', 'Discount')
        return True

    def parse_row(self, item, row):
        """The input is a row from the XLSX spreadsheet that is sent as the remittance advice.
        The parser decides which type of item. Then this does the generic setup"""
        self.manual_correction(item, row)
        item.vat_rate = row['Sage_Tax_Rate']
        item.number = row['Your Ref']
        item.extra_number = row['Our Ref']
        item.date = row['Invoice Date']
        item.member_code = row['Member Code']  # this is not perfect and should perhaps have a more generic name
        # eg sub supplier code.  There should be a one to one correspondence between this code and our supplier
        # codes.  this should tally with code from the reference.
        # print('Member code = {}, {}, MC {}, Ref {}'.format(item.member_code, type(item.member_code),
        #                                        row['Member Code'], row['Your Ref']))
        try:
            v = p(row['Sage_Net_Amount'])
        except TypeError:  # Eg if NetAmount is none
            v = math.nan
        if math.isnan(v):
            # if have value treat using Sage data, if not then used own data nan
            item._gross_amount = p(row['Value'])
            item._vat = p(float(item.gross_amount) / 6)
            item._net_amount = p(item.gross_amount - item.vat)
            item._discount = p(row['Discount'])
            item._set('adj_net_receipt', item.gross_amount)
        else:
            item.set_values(p(row['Sage_Net_Amount']), p(row['Sage_VAT_Amount']), p(row['Discount']))
            self.check_row(item, row)
        # item.net_amount = p(row['Sage_Net_Amount']) # Triggers all the calculations but has to be slightly inaccurate as cannot
        # calculate VAT
        item.customer = row['Account_Ref']
        self.remittance.append(item)

    def parse_ppd_row(self, item, row):
        """The parser decides which type of item. Then this handles the case when the AIS generates a PPD invoice.
        This is different"""
        self.manual_correction(item, row)
        # defaults to UK vat rate which is fint
        item.number = row['Your Ref']
        item.date = row['Invoice Date']
        item.member_code = row['Member Code']
        item._gross_amount = p(row['Value'])
        item._vat = p(float(item.gross_amount) / 6)
        item._net_amount = p(item.gross_amount - item.vat)
        item._discount = p(row['Discount'])

        # print('PPD Member code = {}, {}, MC {}, Ref {}'.format(item.member_code, type(item.member_code),
        #                                        row['Member Code'], row['Your Ref']))
        if p(row['Discount']) != p(0):
            raise RemittanceError('PPD Member code = {} discount should be zero but is {}'.format(
                item.member_code, (row['Discount'])))

        # ?? item.set_values(p(row['Sage_Net_Amount']), p(row['Sage_VAT_Amount']), p(row['Discount']))
        item.customer = row['Account_Ref']
        self.remittance.append(item)

    def add_item(self, row):
        """Add row of data frame to remittance
        """
        if row['Document Type'] == 'Invoice':
            if row['Member Code'] == '4552':
                print('AIS PPD Invoice Row is type {}, member {}'.format(row['Document Type'], row['Member Code']))
                self.parse_ppd_row(AIS_PPD_CreditNote(),
                                   row)  # This is an adjustment by AIS to compensate for the Prompt Payment
                # Discount
            else:
                self.parse_row(AISInvoice(), row)
        elif row['Document Type'] in ('Stop Note', 'EStop Note'):
            self.parse_row(DebitNote(), row)
        elif row['Document Type'] == 'Credit Note':
            if row['Member Code'] == '4552':
                print('AIS PPD Credit Note Row is type {}, member {}'.format(row['Document Type'], row['Member Code']))
                self.parse_row(AIS_PPD_Invoice(),
                               row)  # This is an adjustment by AIS to compensate for the Prompt Payment
                # Discount
            elif row['Member Code'] == '4424':
                print('AIS Agent Invoice Row is type {}, member {}'.format(row['Document Type'], row['Member Code']))
                self.parse_row(AgentInvoice(),
                               row)  # This is an invoice by the agent eg an invoice by AIS for exhibition
                # space
            else:
                # This should be our credit note
                self.parse_row(AISCreditNote(), row)
        elif row['Document Type'] == 'Reverse Stop Note':
            self.parse_row(DebitNoteReversal(), row)
        elif row['Document Type'] == 'Rejected':
            print("** Line marked by AIS as Rejected will be ignored.\n In line |{}|".format(row))
            # Just not parse it
        else:
            raise RemittanceError("Unrecognised line. Document type = {}.\n In line |{}|".format(
                row['Document Type'], row))

    def __init__(self, doc, remittance, manual_correction = dummy_manual_correction):
        self.doc = doc
        self.remittance = remittance
        # TODO implementation of manual_correct is not clean.  Needs to be done in a cleaner fashion
        # eg a transform of the doc.df to another variant with manual corrections applied.
        self.manual_correction = manual_correction
        self.doc_date = doc.payment_date
        remittance.payment_date = doc.payment_date
        remittance.supplier = 'AIS'
        remittance.total = doc.sum_total
        self.doc.df.apply(self.add_item, axis=1)

    def report_df(self):
        return self.doc.df

class ParseItems2(ParseItems):
    """This is specific to AIS.  It parses the data in the Excel sheet.
    This does not use any enrichment from accounting system.  Used to be Sage.
    Once Sage is finally removed this can be renamed back to ParseItems."""

    def parse_row(self, item, row):
        """The input is a row from the XLSX spreadsheet that is sent as the remittance advice.
        The parser decides which type of item. Then this does the generic setup.
        At this stage it is not able to cross check against the accounting entries."""
        self.manual_correction(item, row)
        item.number = row['Your Ref']
        item.extra_number = row['Our Ref']
        item.date = self.doc_date  # This is the date when all the transactions in contra account should take place.
        item.remittance_item_date = row['Invoice Date']  # Date of invoice or transaction this is NOT the date it will
        # be paid in on
        # nor is it the other items should be created
        item.member_code = row['Member Code']  # this is not perfect and should perhaps have a more generic name
        # eg sub supplier code.  There should be a one to one correspondence between this code and our supplier
        # codes.  this should tally with code from the reference.
        # print('Member code = {}, {}, MC {}, Ref {}'.format(item.member_code, type(item.member_code),
        #                                        row['Member Code'], row['Your Ref']))
        item._gross_amount = p(abs(row['Value']))  # Make sure gross amounts are positive even
        # if marked as CR eg for Debit notes
        item._discount = p(abs(row['Discount']))
        #  This is an incomplete record - so for instance the customer is not known.
        self.remittance.append(item)

