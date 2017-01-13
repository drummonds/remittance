"""Utility functions for Remittance"""

def enrich_field(sage, item, field_str, sql_ref):
    """"""
    if not hasattr(item, field_str):
        setattr(item, field_str, sage.using_reference_get(item.number, sql_ref, record_type=['SI']))
    else:  # don't create field
        print('slightly surprised to find {}={} defined for {}'.format(field_str, item.customer, item))


