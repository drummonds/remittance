import datetime as dt
import logging
import sys

from ..remittance import RemittanceException


def today_as_string():
    now = dt.datetime.now()
    return dt.datetime.strftime(now, '%Y-%m-%d')


class SageImportFile:
    """This is the code that glues a remittance document to a SageImport file.  By using the methods you can
    create a file ready for Sage Import.
    Typically it will run all on the create of the class"""

    def __init__(self, remittance, sqldata, name='', file_dir='', auto_run=True, modify_name_if_exists=True):
        """Typically all the code and action of creating the file is driven from constructor."""
        self.sqldata = sqldata
        self.logger = logging.getLogger('SageImportFile')
        self.logger.info('-- Starting SageImportFile setup')
        self.remittance = remittance
        self.tran_date = self.remittance.payment_date
        self.modify_name_if_exists = modify_name_if_exists
        s = self.remittance.supplier.upper()
        if s == 'FENWICK':
            self.bank = '1262'
        elif s == 'AIS':
            self.bank = '1260'
        else:  # Generic contra account
            self.logger.info('** Warning Supplier = {}'.format(s))
            self.bank = '1205'
        self.ran_ok = True
        self.__running_bank_balance = 0
        self.logger.info('-- Ending SageImportFile setup')
        if auto_run:
            self.start_file(name, file_dir)
            try:
                # Do it in this order so that the accumulated discount in the returns can be net off against all the sales.
                self.parse()
            finally:
                self.close_file()

    def check_for_transactions_on_this_day(self, tran_type, account):
        test3 = self.sqldata[self.sqldata['TYPE'] == tran_type]
        test2 = test3[test3['ACCOUNT_REF'] == account]
        test = test2[test2['DATE'] == self.tran_date]
        l = len(test)
        if l == 0:
            comment = 'Found no transactions on {} .'.format(
                self.tran_date.strftime('%Y-%m-%d'), )
            return False, 0, comment
        else:
            tn = test[:1]
            try:
                comment = 'Found {} transactions on {}. First was on {}: details {}: for {}.'.format(
                    l, self.tran_date.strftime('%Y-%m-%d'),
                    list(tn['DATE'])[0].strftime('%Y-%m-%d'),
                    list(tn['DETAILS'])[0],
                    list(tn['AMOUNT'])[0], )
            except:
                comment = 'Error looking for transaction see log'
                self.logger.info('Exception {},\nProblem with test \n{},\ntran_date = {}'.format(sys.exc_info()[0],
                                                                                          test, self.tran_date))
            return True, 0, comment


    def check_accruals_for_stop_note(self, stop_note):
        test3 = self.sqldata[self.sqldata['TYPE'] == 'JD']
        test2 = test3[test3['ACCOUNT_REF'] == 2109]
        test = test2[test2['DETAILS'].str.contains(stop_note)]
        l = len(test)
        if l == 0:
            comment = 'Found no transactions to reverse for reference {} .'.format(stop_note)
            return True, 0, comment
        else:
            tn = test[:1]
            comment = 'Stopnote {}. Found {} transactions on {}. First was on {}: details {}: for {}.'.format(
                stop_note, l, self.tran_date.strftime('%Y-%m-%d'),
                list(tn['DATE'])[0].strftime('%Y-%m-%d'),
                list(tn['DETAILS'])[0],
                list(tn['AMOUNT'])[0], )
            return False, 0, comment

    def stopnote_check_write_row(self, tran_type, nominal, reference,
                                 date, details, net_amount,
                                 tax_code, account='', tax_amount=0.0,
                                 exchange_rate=1, extra_ref='', user_name='H3', comment='', stop_note=''):
        # Todo this should perhaps move to pySage50
        r = self.check_accruals_for_stop_note(stop_note)
        if r[0]:
            # Error There are transactions when there should be none
            self.ran_ok = False
            tran_type = 'xx' + tran_type
            comment = comment + ' ' + r[2]
        else:
            comment = comment + ' :Checked ' + r[2]
        self.si.write_row(tran_type, nominal, reference,
                          date, details, net_amount,
                          tax_code, account=account, tax_amount=tax_amount,
                          exchange_rate=exchange_rate, extra_ref=extra_ref, user_name=user_name, comment=comment)

    def start_file(self, name, file_dir):
        self.si = self.sage_import = SageImport(home_directory=file_dir)
        self.si.start_file(name, modify_name_if_exists=self.modify_name_if_exists)

    def close_file(self):
        self.si.close_file()

    @property
    def running_bank_balance(self):
        return self.__running_bank_balance

    @running_bank_balance.setter
    def running_bank_balance(self, new_balance):
        # For debugging
        self.logger.info('Change in running bank balance = {:,}'.format(new_balance - self.__running_bank_balance))
        self.__running_bank_balance = new_balance

    def parse(self):
        # Create all the transactions into the group account
        # Create running balance
        self.running_bank_balance = 0
        for i in self.remittance.items:
            try:
                i.create_transactions(self)
            except RemittanceException as err:
                self.si.write_error_row("**Exception raised during item: {}".format(err))
            self.logger.info('Calculated running bank balance = {}'.format(self.running_bank_balance))
        try:
            self.remittance.create_transactions(self)  # create final transaction eg moving bank balance
        except RemittanceException as err:
            self.si.write_error_row("**Exception raised during creating final transaction: {}".format(err))


