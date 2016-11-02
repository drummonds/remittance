"""Library for reading in AIS remittance EDI excel sheets.

It checks to make sure that sheet that has been read in actually is self consistent.  There is no difference
in the format for these documents before and after the addition of the prompt payment discount (PPD).

It doesn't cover those EDI documents where there are multiple reports on one sheet.  Where this has
happened in the past (infrequently) the remittance spreadsheet has been edited.

Available classes:

- RemittanceDoc: a holder for a remittance document.

Available functions:

- p: rounding function to pence

"""
from decimal import Decimal, InvalidOperation
import pandas as pd
import re
from sys import exc_info


one_pence = Decimal('0.01')

def p(value):
    "Convert `value` to Decimal pence implementing AIS rounding (up)"
    try:
        #If user_or_username is a User object
        test =  Decimal(value * 100).quantize(one_pence)
        i, d = divmod(test, 1)
        if abs(d) == Decimal(0.50):
            # Implement AIS rounding
            if value > 0:
                result =  (Decimal(value) + Decimal(0.0025)).quantize(one_pence)
            else:
                result =  (Decimal(value) - Decimal(0.0025)).quantize(one_pence)
            print('p Rounding |{}| to {}'.format(value, result))
        else:
            result =  Decimal(value).quantize(one_pence)
    except InvalidOperation:
        print('Invalid Operation Val = |{}|'.format(value))
        t, v, tb = exc_info()
        raise v.with_traceback(tb)
    except TypeError:   #Oops -- didn't works.  ask forgiveness ;-)
        t, v, tb = exc_info()
        if isinstance(value, pd.Series):
            result = pd.Series([ p(x) for x in value])
        else:
            print('Type Error Val = |{}|, {}'.format(value, type(value)))
            raise v.with_traceback(tb)
    return result


