"""Core remittance module

This should define a generic remittance document which is a collection of line items.

"""
import datetime as dt
import math

from h3_yearend import p

class RemittanceException(Exception):
    pass

def na(obj, value, default = 'N/A'):
    try:
        v = getattr(obj, value)
        if math.isnan(v):
            v = 0.0
        return v
    except AttributeError:
        return default


class Remittance():
    """ This is a remittance document object and is a representation of the whole thing.
    # This is a holder for a representation of a generalised remittance document and for operations on that.
    # This at core a list of remittance items.
    # Due to AIS we need take account of the possibility of transforming the lines and lineitems so that
    # the number of output lines and the amounts of the line items might be different to the number of the
    # raw data.
    # Now we need to differentiate between the input raw amounts and output amount.
    # The creation of transaction create null transactions.
    #
    # TODO refactor into
    # - base model for normal used
    # - PPD model inheriting from base model
    # - AIS model peculiarity of AIS
    All properties:
    - items : A list of remittance line items where each refers to a single credit note or invoice.
    """

    def __init__(self):
        self.items = []

    def __repr__(self):
        s = ''
        try:
            s += 'Remittance from {}\n'.format(self.supplier)
        except AttributeError:
            s += 'Remittance from unknown, no supplier set\n'
        if len(self.items) == 0:
            s += 'No items\n'
        else:
            s += str(self.items) + '\n'
        try:
            s += 'Total = {}\n'.format(self.total)
        except AttributeError:
            if len(self.items) != 0:
                s += 'Items but have no total\n'
        try:
            s += 'Payment date {}\n'.format(self.payment_date)
        except AttributeError:
            pass
        return s

    def append(self,item):
        self.items.append(item)

    def addup_template(self, print_calcs, attrib, use_additional_line_items= True):
        sum = p(0)
        if print_calcs:
            print('Inv number, Net, Vat, Gross, Discount, PPD_net, PPD_VAT, PPD_Gross, cust_discount, ' +
                  'cust_discount_vat, ais_discount, ais_discount_vat, adj_net, adj_vat, adj_net_receipt')
        for i in self.items:
            if use_additional_line_items or not(i.additional_line_item):
                if print_calcs:
                    print('{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}'.
                          format(i.number,
                                 na(i, 'net_amount'),  na(i, 'vat'), na(i, 'gross_amount'),
                                 na(i, 'discount'),
                                 na(i, 'ppd_net_amount'), na(i, 'ppd_vat'), na(i, 'ppd_gross_amount'),
                                 na(i, 'cust_discount'), na(i, 'cust_discount_vat'),
                                 na(i, 'ais_discount'), na(i, 'ais_discount_vat'),
                                 na(i, 'adj_net'), na(i, 'adj_vat'), na(i, 'adj_net_receipt'),
                                )
                          )
                sum += p(na(i, attrib, 0))
            else: # Just show what is being skipped
                if print_calcs:
                    print('Addup template skipping {} for {}'.format(p(na(i, attrib, 0)), i))
        return sum

    def addup(self, print_calcs = False):
        return self.addup_template(print_calcs, 'adj_net_receipt', False)

    def check_lineitem_sum_using_calculated_discounts(self, addup_func, msg):
        all_ok = True
        # Make sure sum of items equals total
        sum = addup_func()
        if p(self.total) == p(sum):
            print('Total{} checked = {}'.format(msg, p(self.total)))
        else:
            all_ok = False
            addup_func(True)
            print('Line Item Sum using calculated discounts (adj_net_receipt)')
            print('Problem with {} calculated sum of items = {} but printed total = {}, diff = {}\n'.format(
                    msg, p(sum), p(self.total), p(sum)-p(self.total)))
        return all_ok

    def check_PPD(self):
        """Check that there are only a small number of PPD lines from AIS.
        You can get multiple items if the first item is not in credit and so the deduction rolls over
        to the next week.  I am setting an arbitrary small limit in the code.
        There should actually be only one = invoice and a small number of credit notes.
        """
        # TODO This code should be taken out and inserted by the code that parses for the AIS_PPD
        all_ok = True
        count = 0
        self.calc_ais_ppd_gross_sum = p(0)
        for i in self.items:
            if type(i) in (AIS_PPD_Invoice, AIS_PPD_CreditNote, ):
                ppd = i
                count += 1
                self.calc_ais_ppd_gross_sum += p(ppd.gross_amount)
                if type(i) in (AIS_PPD_Invoice, ):
                    the_invoice = i
        if count <= 3 and count > 0:
            print('Good, small {} number of AIS PPD gross of all = {}'.format(count, self.calc_ais_ppd_gross_sum))
            gross = p(-self.calc_ais_ppd_gross_sum)
            inv = p(self.ais_invoice)
            if gross != inv:
                all_ok = False
                raise RemittanceException('PPD gross amount {} != AIS invoice amount {}'.format(gross, inv))

        else:
            all_ok = False
            print('Instead of a small number there are {} AIS PPD line items.'.format(count))
        return all_ok

    def self_check(self):
        print('Calculate sums of each property')
        for f in ['net_amount', 'vat', 'gross_amount', 'discount', 'ppd_net_amount', 'ppd_vat',
                  'ppd_gross_amount', 'ppd_gross_amount_a', 'ppd_vat_a']:
            sum = self.addup_template(False, f, False)
            print('  Sum of {} = {}'.format(f, sum))
        if not all([self.check_lineitem_sum_using_calculated_discounts(self.addup,
                                                                       'Line item sum using calculated discounts'),
                    self.check_PPD()]):
            raise RemittanceException('Self check of remittance failed')


class AbstractInvoiceLineItem():
    """
    Properties:
    - net_amount : The input amount excluding VAT and excluding discounts
        This should match the invoiced amount.
    - VAT : The VAT due on the net amount
    - Gross_amount: net_amount + VAT
    - ppd_net_amount : The net amount after the prompt payment discount (there are two ways to calculate this which are
      not the same.
    - ppd_vat : VAT on ppd_net_amount
    - ppd_gross_amount : The gross amount for PPD

    """

    def _set(self, attrib, value):
        rounded_value = p(value)  # If output amount has not been set set as raw_amount as default
        if not hasattr(self,'_'+attrib):
            setattr(self, '_'+attrib, rounded_value)
        else:
            if abs(getattr(self, '_'+attrib) - rounded_value) < 0.1:
                raise RemittanceException('Trying to set {} with {} when it already was {}.  likely rounding error'.format(
                    attrib, rounded_value, getattr(self, '_'+attrib)))

    def set_values(self, net_amount, vat, discount):
        """Set both values to eliminate rounding errors plus discount
        For AIS  cust_discount + cust_discount_vat = discount
        If calculated this might be out by a 1 p.  This should be taken by us as the calculation should match the
        the invoice calculation.
        So the cust_discount is calculated by  discount - cust_discount_vat
        """
        self._net_amount = p(net_amount)
        self._vat =  p(vat)
        self._set('gross_amount', self.net_amount + self.vat)
        self._discount = p(discount)
        self.calculate_discount_amounts()
        # Make the adjustments for rounding
        self._cust_discount = self.discount - self.cust_discount_vat # This is a recalculation as first time
        # cust_discount_vat depends on cust_discount


    def calculate_discount_amounts(self):
        # Gross customer discount
        self._set('ppd_net_amount', self.net_amount - self.discount)
        self._set('ppd_vat', float(self.ppd_net_amount) * self.vat_rate)
        self._set('ppd_gross_amount', self.ppd_net_amount + self.ppd_vat)
        self._set('ppd_gross_amount_a', float(self.ppd_net_amount) * (1+ self.vat_rate))
        self._set('ppd_vat_a', self.ppd_gross_amount_a - self.ppd_net_amount)
        self._set('cust_discount', float(self.net_amount) * self.cust_discount_rate)
        self._set('cust_discount_vat', float(self.cust_discount) * self.vat_rate)
        self._set('ais_discount', float(self.net_amount) * self.ais_discount_rate)
        self._set('ais_discount_vat', float(self.ais_discount) * self.ais_vat_rate)
        self._set('adj_net_receipt', self.gross_amount - self.discount - self.ais_discount - self.ais_discount_vat)
        # The net receipt is two parts as the AIS part is dealt with seperately
        self._set('adj_vat', self.ppd_vat)
        self._set('adj_net', self.gross_amount - self.ppd_vat - self.cust_discount - self.cust_discount_vat
                  - self.ais_discount - self.ais_discount_vat)


    @property
    def net_amount(self):
        return self._net_amount


    @net_amount.setter
    def net_amount(self, value):
        self._net_amount = p(value)
        self._set('vat', float(value) * self.vat_rate) # This doesn't work as the invoice is calculated from line items
        # up and so can be different from the total by 0.5p a line item.
        self._set('gross_amount', self.net_amount + self.vat)
        self._set('discount', float(self.net_amount) * self.cust_discount_rate * (1+ self.vat_rate))
        self.calculate_discount_amounts()

    @property
    def vat(self):
        return self._vat

    @vat.setter
    def vat(self, value):
        self._set('vat', value)

    @property
    def gross_amount(self):
        return self._gross_amount

    @gross_amount.setter
    def gross_amount(self, value):
        self._set('gross_amount', value)

    @property
    def discount(self):
        return self._discount

    @discount.setter
    def discount(self, value):
        self._set('discount', value)

    @property
    def ppd_net_amount(self):
        return self._ppd_net_amount

    @ppd_net_amount.setter
    def ppd_net_amount(self, value):
        self._set('ppd_net_amount', value)

    @property
    def ppd_vat(self):
        return self._ppd_vat

    @ppd_vat.setter
    def ppd_vat(self, value):
        self._set('ppd_vat', value)

    @property
    def ppd_gross_amount(self):
        return self._ppd_gross_amount

    @ppd_gross_amount.setter
    def ppd_gross_amount(self, value):
        self._set('ppd_gross_amount', value)

    @property
    def ppd_vat_a(self):
        return self._ppd_vat_a

    @ppd_vat_a.setter
    def ppd_vat_a(self, value):
        self._set('ppd_vat_a', value)

    @property
    def ppd_gross_amount_a(self):
        return self._ppd_gross_amount_a

    @ppd_gross_amount_a.setter
    def ppd_gross_amount_a(self, value):
        self._set('ppd_gross_amount_a', value)

    @property
    def cust_discount(self):
        return self._cust_discount

    @cust_discount.setter
    def cust_discount(self, value):
        self._set('cust_discount', value)

    @property
    def cust_discount_vat(self):
        return self._cust_discount_vat

    @cust_discount_vat.setter
    def cust_discount_vat(self, value):
        self._set('cust_discount_vat', value)

    @property
    def ais_discount(self):
        return self._ais_discount

    @ais_discount.setter
    def ais_discount(self, value):
        self._set('ais_discount', value)

    @property
    def ais_discount_vat(self):
        return self._ais_discount_vat

    @ais_discount_vat.setter
    def ais_discount_vat(self, value):
        self._set('ais_discount_vat', value)

    @property
    def adj_net(self):
        return self._adj_net

    @adj_net.setter
    def adj_net(self, value):
        self._set('adj_net', value)

    @property
    def adj_vat(self):
        return self._adj_vat

    @adj_vat.setter
    def adj_vat(self, value):
        self._set('adj_vat', value)

    @property
    def adj_net_receipt(self):
        return self._adj_net_receipt

    @adj_net_receipt.setter
    def adj_net_receipt(self, value):
        self._set('adj_net_receipt', value)

    def __init__(self):
        self.number = ''
        self.date = dt.datetime(1900, 1, 1, 0, 0, 0)
        self.additional_line_item = False # Some line items are added in and are not in Sage eg PPD and debit notes
        # So may need to exclude these when checking against the original item
        # self.invoiced is set up later which is the invoice amount
        # self.customer is set up later by enrichment from the number and data in the accounting system
        self.vat_rate = 0.2
        self.ais_vat_rate = 0.2 # AIS charges VAT on its 1% even if the customer is VAT exempt.
        self.cust_discount_rate = 0.05
        self.ais_discount_rate = 0.01

    def __repr__(self):
        s = '{} on {} for (full price) {} with VAT {}'.format(self.number, self.date, self.net_amount, self.vat)
        try:
            s += ' customer = {}'.format(self.customer)
        except AttributeError:
            pass
        s += '\n'
        return s

    def __str__(self):
        return ' Abstract type {}'.format(repr(self))

    def create_transactions(self, file):
        raise RemittanceException("Abstract type. {}".format(self))

class Invoice(AbstractInvoiceLineItem):
    """Normal Invoice"""

    def __str__(self):
        return ' Invoice {}'.format(repr(self))

    def create_transactions(self, file):
        if self.gross_amount > 0:
            comment = ''
            #Todo this discount calculation should be moved to invoice and also checked.
            if self.discount > 0:
                file.check_write_row('SC', '4009', file.remittance.supplier+' '+self.number, self.date,
                            'Sales Discount '+self.number,
                            self.calc_discount, 'T1', tax_amount = self.calc_discount_vat,
                            comment = comment, account = self.customer)
                # No impact on running bank balance
            cash_in = self.gross_amount-self.discount
            file.check_write_row('SA', file.bank, file.remittance.supplier+' '+self.number, self.date,
                               'Sales Receipt '+self.number,
                               cash_in, 'T9', comment = comment, account = self.customer)
            file.running_bank_balance += cash_in
        elif self.gross_amount == 0:
            print("Invoice has zero amount which is a little odd. {}".format(self))
        else:
            raise RemittanceException("Invoice has negative amount which is definitely odd. {}".format(self))

class AISInvoice(Invoice):

    def __str__(self):
        return ' AIS Invoice {}'.format(repr(self))

    def create_transactions(self, file):
        if self.net_amount > 0:
            comment = ''
            if self.discount > 0:
                file.check_write_row('SC', '4009', file.remittance.supplier+' '+self.number, self.date,
                            'Sales Discount '+self.number + ' Customer discount',
                            self.cust_discount, 'T1', tax_amount = self.cust_discount_vat,
                            comment = comment, account = self.customer)
                # No impact on running bank balance
            receipt = self.adj_net_receipt + self.ais_discount + self.ais_discount_vat
            file.check_write_row('SA', file.bank, file.remittance.supplier+' '+self.number, self.date,
                               'Sales Receipt '+self.number+' after customer and AIS discounts and adjusted for rounding',
                               receipt, 'T9', comment = comment, account = self.customer)
            file.running_bank_balance += receipt
        elif self.gross_amount == 0:
            print("Invoice has zero amount which is a little odd. {}".format(self))
        else:
            raise RemittanceException("Invoice has negative amount which is definitely odd. {}".format(self))

class AgentInvoice(AbstractInvoiceLineItem):
    """This invoice is an invoice from the agent which appears like a credit note"""

    def __str__(self):
        return ' Agent Invoice {}'.format(repr(self))


    def calc_discount(self):
        return 0

    def create_transactions(self, file):
        if self.gross_amount < 0: # The amount is like a credit note but is in fact a positive payment on advance
            comment = ''
            #Todo this discount calculation should be moved to invoice and also checked.
            if p(self.calc_discount()) != 0:
                raise RemittanceException('Agent Invoice ({}) should not have a discount.'.format(self))
            file.check_write_row('PA', file.bank, self.member_code+' '+self.number, self.date,
                               'Sales Receipt '+self.number,
                               -self.gross_amount, 'T9', comment = comment, account = 'AIS001') # TODO should make variable
            file.running_bank_balance -= self.gross_amount
        elif self.gross_amount == 0:
            print("Agent Invoice has zero amount which is odd, {}".format(self))
        else:
            raise RemittanceException("Agent Invoice has positive amount which is definitely odd " +
                                      " (should be negative like a credit note). {}".format(self))

class DebitNote(AbstractInvoiceLineItem):

    def __str__(self):
        return ' Debit Note {}'.format(repr(self))

    def create_transactions(self, file):
        if p(self.net_amount) == p(-315.18): # Todo add check for member code
            file.check_write_row('PA', file.bank, 'Bentalls', self.date,
                               'Bentalls Salary Consultancy '+self.number,
                               -self.gross_amount, 'T9', comment = 'comment', account = 'BEN001')
            file.running_bank_balance -= self.gross_amount
        elif self.net_amount < 0:
            # Todo check that there is not already an entry in 2109 for this credit note
            # todo check and add this entry to the list of debits notes
            # todo notify Treez of this issue
            accrual = -(self.gross_amount - self.discount)
            tran_type = 'DN '+file.remittance.supplier
            ref_prefix = 'Waiting for reversal; temporarily '+self.number
            file.write_row('JD', '2109', tran_type, self.date, ref_prefix + ' into accrual', accrual, 'T9')
            file.write_row('JC', file.bank, tran_type, self.date, ref_prefix + ' from bank account', accrual, 'T9')
            file.running_bank_balance -= accrual
        else:
            raise RemittanceException("Debit note has zero or positive amount which is odd. {}".format(self))

class DebitNoteReversal(AbstractInvoiceLineItem):

    def __str__(self):
        return ' Debit Note Reversal {}'.format(repr(self))

    def create_transactions(self, file):
        if self.net_amount > 0:
            # Todo check that there is not already an entry in 2109 for this credit note
            # todo check and add this entry to the list of debits notes
            # todo notify Treez of this issue
            comment = 'Manual check that this is reversing a stop note in 2109 then remove xx on type'
            accrual = (self.gross_amount - self.discount)
            tran_type = 'RDN '+file.remittance.supplier
            ref_prefix = 'Waiting for reversal; temporarily '+self.number
            file.write_row('xxJC', '2109', tran_type, self.date, ref_prefix + ' into accrual', accrual,
                           'T9', comment = comment)
            file.write_row('xxJD', file.bank, tran_type, self.date, ref_prefix + ' from bank account',
                           accrual, 'T9', comment = comment)
            file.running_bank_balance += accrual
        else:
            raise RemittanceException("Debit note reversal has zero or positive amount which is odd. {}".format(self))

class AISCreditNote(AbstractInvoiceLineItem):

    def __str__(self):
        return ' AIS Credit Note {}'.format(repr(self))

    def create_transactions(self, file):
        if self.net_amount < 0:
            comment = ''
            # self.check_write_row('SD', '4009', 'AIS', self.tran_date, 'Sales Discount '+r.Reference,
            #           r.Discount2, 'T9', account = r.Customer)
            if self.cust_discount < 0:
                file.check_write_row('SI', '4009', file.remittance.supplier+' '+self.number, self.date,
                            'CN Discount for '+self.number + ' Reverse Customer discount',
                            -self.cust_discount, 'T1', tax_amount = -self.cust_discount_vat,
                            comment = comment, account = self.customer)
            receipt = self.adj_net_receipt + self.ais_discount + self.ais_discount_vat
            file.check_write_row('SP', file.bank, file.remittance.supplier, self.date,
                               'Credit Note '+self.number+ ' After reversing customer and AIS discounts (& rounding)',
                               -receipt, 'T9', comment = comment, account = self.customer)
            file.running_bank_balance += receipt
        else:
            raise RemittanceException("Credit note has zero or positive amount which is odd. {}".format(self))


class CreditNote(AbstractInvoiceLineItem):

    def __str__(self):
        return ' Credit Note {}'.format(repr(self))

    def create_transactions(self, file):
        if self.gross_amount < 0:
            comment = ''
            # self.check_write_row('SD', '4009', 'AIS', self.tran_date, 'Sales Discount '+r.Reference,
            #           r.Discount2, 'T9', account = r.Customer)
            if self.calc_discount() < 0:
                file.write_row('JD', file.bank, 'Discount', self.date,
                        'CN Discount for '+self.number, -self.calc_discount(), 'T9')
                file.running_bank_balance -= self.calc_discount()
                file.write_row('JC', '4009', 'Discount', self.date,
                        'CN Discount for '+self.number, -self.calc_discount(), 'T9')
            file.check_write_row('SP', file.bank, file.remittance.supplier, self.date,
                               'Credit Note '+self.number,
                               -self.invoiced, 'T9', comment = comment, account = self.customer)
            file.running_bank_balance += self.invoiced
        else:
            raise RemittanceException("Credit note has zero or positive amount which is odd. {}".format(self))




class AIS_PPD_Invoice(AbstractInvoiceLineItem):
    """ In order to to make the adjustments for the prompt payment discount VAT directive.  AIS have inserted
    an additional line item into the statement that they send us.  This is meant to be take account of the adjustments
    that need to be made to reduce the amount of VAT that we need to pay to HMRC ( and our customers need to pay to us).
    There should be one and only invoice entry like this in the Remittance. However there might be multiple credit item
    amounts.  They should all be added up.
    TODO  Need to create an entry which matches up to the prompt payment discount aggregate.
    """

    def __init__(self):
        super(AIS_PPD_Invoice, self).__init__()
        self.additional_line_item = True # AIS added this line

    def __str__(self):
        return ' AIS PPD Invoice {}'.format(repr(self))

    def create_transactions(self, file):
        if self.gross_amount < 0:
            comment = ''
            file.check_write_row('PI', '4009', self.member_code+' '+self.number, self.date,
                            'AIS 1% discount {} {}'.format(self.extra_number, self.number),
                            -self.net_amount, 'T1', tax_amount = -self.vat,
                            comment = comment, account = 'AIS001')  # TODO should make account variable
            file.check_write_row('PA', file.bank, file.remittance.supplier, self.date,
                                     'AIS 1% discount {} {}'.format(self.extra_number, self.number),
                                     - self.adj_net_receipt, 'T9', comment = comment, account = 'AIS001')
            file.running_bank_balance += self.adj_net_receipt
        else:
            raise RemittanceException("AIS PPD Invoice note has zero or negative amount which is odd. {}".format(self))


class AIS_PPD_CreditNote(AbstractInvoiceLineItem):
    """ In order to to make the adjustments for the prompt payment discount VAT directive.  AIS have inserted
    an additional line item into the statement that they send us.  This is meant to be take account of the adjustments
    that need to be made to reduce the amount of VAT that we need to pay to HMRC ( and our customers need to pay to us).
    There should be one and only invoice entry like this in the Remittance. However there might be multiple credit item
    amounts.  They should all be added up.
    TODO  Need to create an entry which matches up to the prompt payment discount aggregate.
    """

    def __init__(self):
        super(AIS_PPD_CreditNote, self).__init__()
        self.additional_line_item = True # AIS added this line

    def __str__(self):
        return ' AIS PPD Credit Note {}'.format(repr(self))

    def create_transactions(self, file):
        if self.gross_amount > 0:
            comment = ''
            file.check_write_row('PC', '4009', self.member_code+' '+self.number, self.date,
                            'AIS 1% discount '+self.number,
                            self.net_amount, 'T1', tax_amount = self.vat,
                            comment = comment, account = 'AIS001')
            # There won't be a credit unless there is more payment so this is aggregated into the PPD Invoice
            # file.check_write_row('PP', file.bank, file.remittance.supplier, self.date,
            #                         'AIS 1% discount '+self.number,
            #                         -self.gross_amount, 'T9', comment = comment, account = 'AIS001')
            # file.running_bank_balance -= self.gross_amount
        else:
            raise RemittanceException("AIS PPD Credit note has zero or positive amount which is odd. {}".format(self))
