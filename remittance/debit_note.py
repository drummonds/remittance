from .remittance import RemittanceException
from .remittance import AbstractInvoiceLineItem
from .utils import p


class DebitNote(AbstractInvoiceLineItem):
    """gross_amount"""

    def __str__(self):
        return ' Debit Note {}'.format(repr(self))

    def enrich(self, remittance_doc, sage):
        """Enrichment is slightly trickier as may not be able to find correct supplier.
        The aim is to add additional information from the accounting database
        """
        invoice_number = self.number  # This is the debit note number
        pass

    def create_transactions(self, sage_import_file):
        rd = sage_import_file
        si = sage_import_file.sage_import
        supplier = rd.remittance.supplier.upper()
        cash_out = self.gross_amount - self.discount
        if supplier == 'FENWICK' and p(cash_out) in (p(315.18), p(321.48),): # Todo add check for member code
            # TODO specific to Fenwick. Make generic and create specific Fenwick and have a way of inserting
            si.detailed_check_write_row('PA', rd.bank, 'Bentalls',
                                        rd.tran_date,  # see first check_write_row in Invoice.create_transactions
                                        'Bentalls Salary Consultancy '+self.number,
                                        cash_out, 'T9', comment = 'comment', account = 'BEN001')
            rd.running_bank_balance -= self.gross_amount
        elif self.gross_amount < 0:
            # Todo check that there is not already an entry in 2109 for this credit note
            # todo check and add this entry to the list of debits notes
            # todo notify Treez of this issue
            # Todo The Fenwick cash out is positive - we should change the default sign of this as well on parsing.
            accrual = -(self.gross_amount - self.discount)
            tran_type = 'DN '+rd.remittance.supplier
            ref_prefix = 'Waiting for reversal; temporarily '+self.number
            si.detailed_check_write_row('JD', '2109', tran_type, self.date, ref_prefix + ' into accrual', accrual, 'T9')
            si.detailed_check_write_row('JC', rd.bank, tran_type, self.date, ref_prefix + ' from bank account', accrual, 'T9')
            rd.running_bank_balance -= accrual
        else:
            raise RemittanceException("Debit note has zero or positive amount which is odd. {}".format(self))


class DebitNoteReversal(AbstractInvoiceLineItem):

    def __str__(self):
        return ' Debit Note Reversal {}'.format(repr(self))

    def create_transactions(self, sage_import_file):
        rd = sage_import_file
        si = sage_import_file.sage_import
        if self.net_amount > 0:
            # Todo check that there is not already an entry in 2109 for this credit note
            # todo check and add this entry to the list of debits notes
            # todo notify Treez of this issue
            comment = 'Manual check that this is reversing a stop note in 2109 then remove xx on type'
            accrual = (self.gross_amount - self.discount)
            tran_type = 'RDN '+rd.remittance.supplier
            ref_prefix = 'Waiting for reversal; temporarily '+self.number
            si.detailed_check_write_row('xxJC', '2109', tran_type, self.date, ref_prefix + ' into accrual', accrual,
                           'T9', comment = comment)
            si.detailed_check_write_row('xxJD', rd.bank, tran_type, self.date, ref_prefix + ' from bank account',
                           accrual, 'T9', comment = comment)
            rd.running_bank_balance += accrual
        else:
            raise RemittanceException("Debit note reversal has zero or positive amount which is odd. {}".format(self))

