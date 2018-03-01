from .remittance import RemittanceException
from .remittance import AbstractInvoiceLineItem
from .utilities import enrich_field
from .utils import p


class Invoice(AbstractInvoiceLineItem):
    """Normal Invoice"""

    def __str__(self):
        return ' Invoice {}'.format(repr(self))

    def enrich(self, remittance_doc, sage):
        """Enrich a raw remittance document with data from Sage
        This is designed specifically for
        It uses getField which uses 3 predefined columns:
            'Your Ref'  is our invoice number
            'Member Code' is an AIS specfic membership code and defines some exceptions
            'Document Type' defines the type of document.  We are only enriching 'Invoice' and 'Credit Note'

        Worked example on calcs:
            Inputs
    Sage	Invoiced	2142.24
    constant	Discount rate	2.50%
     - calc	Discount	53.56
     - calc	net amount	2088.68
        net discount	44.63
        vat discount	8.93

    Fenwick	Gross	2133.31
    Fenwick	Discount	44.63
     - calc	Net Cash	2088.68

        """
        invoice_number = self.number  # This is the invoice number
        enrich_field(sage, self, 'customer', 'ALT_REF')
        enrich_field(sage, self, 'invoiced', 'AMOUNT')
        if p(self.invoiced) == p(self.gross_amount):  # Paying the full amount
            if self.discount > 0:
                raise RemittanceException('Gross amount on remittance advice ' +
                                          '{} matches invoice {} from {} but discount {} is greater than zero'.format(
                                              p(self.gross_amount), invoice_number, self.customer, self.discount))
        else:  # Paying less the full amount so assuming should be taking advantage of prompt payment
            self.gross_prompt_payment_discount = p(float(self.invoiced) * remittance_doc.cust_discount_rate)
            self.net_prompt_payment_discount = p(float(self.gross_prompt_payment_discount)
                                                 / (1 + self.vat_rate))
            self.prompt_payment_discount_vat = ((self.gross_prompt_payment_discount)
                                                - p(self.net_prompt_payment_discount))
            self.calc_net_amount = p(self.invoiced) - p(self.gross_prompt_payment_discount)
            self.net_cash_in = p(self.gross_amount - self.discount)
            if self.calc_net_amount != self.net_cash_in:
                if abs(self.calc_net_amount - self.net_cash_in) < p(0.05):  # Small rounding error will adjust discount
                    # to align with actual cash received.
                    # so self.net_cash_in is assumed to be correct
                    # & self.invoiced is correct as from accounts
                    self.net_prompt_payment_discount = p(self.invoiced
                                                         - self.prompt_payment_discount_vat - self.net_cash_in)
                    self.gross_prompt_payment_discount = (self.net_prompt_payment_discount
                                                          + self.prompt_payment_discount_vat)
                    self.calc_net_amount = p(self.invoiced) - p(self.gross_prompt_payment_discount)
                else:  # Discount >= 0.05
                    raise RemittanceException(
                        'Calculated net payment after prompt payment discount does not match receipt.\n' +
                        '  Invoiced amount        : {}'.format(p(self.invoiced)) +
                        '  Prompt payment discount: {}'.format(p(self.gross_prompt_payment_discount)) +
                        '  Calculated net amount  : {}'.format(p(self.calc_net_amount)) +
                        ' On remittance:' +
                        '  Gross amount: {}'.format(p(self.gross_amount)) +
                        '  Discount: {}'.format(p(self.discount)) +
                        '  Net Cash: {}'.format(self.net_cash_in)
                    )
        enrich_field(sage, self, 'outstanding', 'OUTSTANDING')
        if self.outstanding == p(0) and self.gross_amount > 0:
            raise RemittanceException(
                'Outstanding amount is zero for invoice {} from {} must have already been entered'.format(
                    invoice_number, self.customer))


    def create_transactions(self, sage_import_file):
        """This creates transactions such as payments and credits at some later date."""
        rd = sage_import_file
        si = sage_import_file.sage_import
        if self.gross_amount > 0:
            comment = ''
            # The VAT on the prompt payment discount is recoverable
            if self.discount > 0:
                si.detailed_check_write_row('SC', '4009', rd.remittance.supplier+' '+self.number,
                                            rd.tran_date,  # Use the file transaction date as this is when the
                                            # transaction takes place. Previously (in error) used self.date which is the
                                            # date the invoice was raised.  (Referenced from below)
                                            'Sales Discount '+self.number,
                                            self.net_prompt_payment_discount, 'T1',
                                            tax_amount = self.prompt_payment_discount_vat,
                                            comment = comment, account = self.customer)
                # No impact on running bank balance
            cash_in = self.gross_amount - self.discount
            si.detailed_check_write_row('SA', rd.bank, rd.remittance.supplier+' '+self.number,
                                        rd.tran_date,  # see first check_write_row in Invoice.create_transactions
                                        'Sales Receipt '+self.number,
                                        self.calc_net_amount, 'T9', comment = comment, account = self.customer)
            rd.running_bank_balance += cash_in
        elif self.gross_amount == 0:
            print("Invoice has zero amount which is a little odd. {}".format(self))
        else:
            raise RemittanceException("Invoice has negative amount which is definitely odd. {}".format(self))


