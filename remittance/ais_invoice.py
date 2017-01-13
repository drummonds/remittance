from .remittance import RemittanceException
from .invoice import Invoice


class AISInvoice(Invoice):

    def __str__(self):
        return ' AIS Invoice {}'.format(repr(self))

    def create_transactions(self, sage_import_file):
        rd = sage_import_file
        si = sage_import_file.sage_import
        if self.net_amount > 0:
            comment = ''
            if self.discount > 0:
                si.detailed_check_write_row('SC', '4009', rd.remittance.supplier+' '+self.number,
                                     rd.tran_date,  # see first check_write_row in Invoice.create_transactions
                                     'Sales Discount '+self.number + ' Customer discount',
                                     self.cust_discount, 'T1', tax_amount = self.cust_discount_vat,
                                     comment = comment, account = self.customer)
                # No impact on running bank balance
            receipt = self.adj_net_receipt + self.ais_discount + self.ais_discount_vat
            si.detailed_check_write_row('SA', rd.bank, rd.remittance.supplier+' '+self.number,
                                 rd.tran_date,  # see first check_write_row in Invoice.create_transactions
                                 'Sales Receipt '+self.number+' after customer and AIS discounts and adjusted for rounding',
                                 receipt, 'T9', comment = comment, account = self.customer)
            rd.running_bank_balance += receipt
        elif self.gross_amount == 0:
            print("Invoice has zero amount which is a little odd. {}".format(self))
        else:
            raise RemittanceException("Invoice has negative amount which is definitely odd. {}".format(self))

