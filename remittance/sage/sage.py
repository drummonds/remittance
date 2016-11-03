"""Interface to Sage accounting ODBC

This provides an interface to extract data from the accounting system.

It works by extracting the data into a Pandas dataframe and then doing queries from that.

"""
import numpy as np
import pandas as pd
import pyodbc

from h3_yearend import p

class SageError(Exception):
    pass

class Sage():
    """Interface to SAGE line 50 account system.
    """
    def  __init__(self):
        cnxn = pyodbc.connect("DSN=Slumberfleece2015;UID=h3")
        #cnxn = pyodbc.connect("DSN=Slumberfleece2014;UID=h3;PWD=h3")
        sql= """
SELECT
    tc.TAX_RATE, sl.DEF_TAX_CODE, ah.TRAN_NUMBER, ah.TYPE, ah.DATE, ah.ACCOUNT_REF, ah.INV_REF,
    ah.GROSS_AMOUNT, ah.FOREIGN_GROSS_AMOUNT, ah.BANK_FLAG, ah.NET_AMOUNT, ah.TAX_AMOUNT
FROM
AUDIT_HEADER ah, SALES_LEDGER sl, TAX_CODE tc
WHERE
(ah.ACCOUNT_REF = sl.ACCOUNT_REF)
AND sl.DEF_TAX_CODE = tc.TAX_CODE
AND ah.DELETED_FLAG = 0
"""
        self.sqldata = pd.read_sql(sql, cnxn)
        if self.sqldata['DATE'].dtype == np.object:
            self.sqldata['DATE'] = self.sqldata['DATE'].astype('datetime64')
        #print(len(sqldata))
        #sqldata.head(1)

    def using_invoice_get(self, i, field):
        """
        Using the invoice number we can look up the field.  The accounting database contains line entries
        """
        df = self.sqldata[self.sqldata['INV_REF'].str.contains(str(i))]
        result = ''
        if len(df) == 1: # Have found some line entries for this invoice reference
            return df.iloc[0][field]
        else:
            if len(df) == 0:
                raise SageError('No data found in Audit Header to match invoice {}'.format(i))
            else:
                raise SageError('Multiple ({}) records found in Audit Header to match invoice {}'.format(len(df),i))

    def get_field(self, row, field):
        """ For use in a lambda
         lambda row: self.get_field(row,'This Field')
        """
        result = None
        if row['Member Code'] not in ('4552', '4424'): # Ignore enrichment for AIS discount and AIS invoices
            if row['Document Type'] in ('Invoice', 'Credit Note',):
                result = self.using_invoice_get(row['Your Ref'], field)
        return result

    def enrich_remittance_doc(self, remittance_doc):
        """Enrich a raw remittance document with data from Sage
        """
        def get_series(field):
            return remittance_doc.df.apply(lambda row: self.get_field(row,field), axis = 1)

        remittance_doc.df['Account_Ref'] = get_series('ACCOUNT_REF')
        remittance_doc.df['Sage_Net_Amount'] = get_series('NET_AMOUNT')
        remittance_doc.df['Sage_Gross_Amount'] = get_series('GROSS_AMOUNT')
        remittance_doc.df['Sage_VAT_Amount'] = get_series('TAX_AMOUNT')
        remittance_doc.df['Sage_Tax_Rate'] = get_series('TAX_RATE') / 100
        net = remittance_doc.df['Sage_Net_Amount'].sum()
        vat = remittance_doc.df['Sage_VAT_Amount'].sum()
        gross = remittance_doc.df['Sage_Gross_Amount'].sum()
        # Check sage calculations - shouldn't be a problem.  if this is passed can then rely on two of the
        # three values to set the third.  Note due to rounding you can't calculate them except approximately unless
        # you have access to the line items.
        if ( p(net + vat) != p(gross) ):
            remittance_doc.checked = False
            raise SageError("Internal calcs of sum in Sage don't add up. net + vat != gross,  {} + {} != {}".format(
                net, vat, gross
            ))
        # Check that gross AIS doc values match Sage gross values
        gross_sum_ex_discount = remittance_doc.df[remittance_doc.df['Member Code'] != '4552']['Sage_Gross_Amount'].sum()
        if ( gross != gross_sum_ex_discount ):
            remittance_doc.checked = False
            raise SageError("Adding up total AIS invoices doesn't equal Sage sum,  {} != {}, types {}, {}".format(
                gross_sum_ex_discount, gross, type(gross_sum_ex_discount), type(gross)
            ))
        # The internal sum has already been done.  It is not until the next stage that we calculate discounts
