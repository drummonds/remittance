"""Conversion remittance module

This converts a remittance document as received into a gneralised remittance.

"""
class ParseItems():

    def parse_row(self, item, row):
        item.number = row['Your Ref']
        item.date = row['Invoice Date']
        item.raw_amount = p(row['Value'])
        item.raw_discount = p(row['Discount'])
        item.member_code = row['Member Code'] # this is not perfect and should perhaps have a more generic name
            # eg sub supplier code.  There should be a one to one correspondence between this code and our supplier
            # codes.  this should tally with code from the reference.
        self.remittance.append(item)

    def add_item(self, row):
        """Add row of data frame to remittance
        """
        if row['Document Type'] == 'Invoice':
            self.parse_row(Invoice(), row)
        elif row['Document Type'] in ('Stop Note', 'EStop Note'):
            self.parse_row(DebitNote(), row)
        elif row['Document Type'] == 'Credit Note':
            if row['Member Code'] == '4552':
                print('Row is type {}, member {}'.format(row['Document Type'], row['Member Code']))
                self.parse_row(AIS_PPD(), row) # This is an adjustment by AIS to compensate for the Prompt Payment
                   # Discount
            elif row['Member Code'] == '4424':
                self.parse_row(AgentInvoice(), row) # This is an invoice by the agent eg an invoice by AIS for exhibition
                   # space
            else:
                # This should be our credit note
                self.parse_row(CreditNote(), row)
        elif row['Document Type'] == 'Reverse Stop Note':
            self.parse_row(DebitNoteReversal(), row)
        elif row['Document Type'] == 'Rejected':
            print("** Line marked by AIS as Rejected will ignore.. Document type = {}.\n In line |{}|".format(
                    row['Document Type'], row))
        else:
            raise RemittanceException("Unrecognised line. Document type = {}.\n In line |{}|".format(
                    row['Document Type'], row))

    def convert_raw_remittance(self, doc, remittance):
        self.doc = doc
        self.remittance = remittance
        doc_date = doc.payment_date
        remittance.payment_date = doc.payment_date
        remittance.supplier = 'AIS'
        remittance.total = doc.sum_total
        self.doc.df.apply(self.add_item, axis = 1)
        # Now that have all the data can now apply the recalculation.
        remittance.calculate_final_from_raw()


# ais = Remittance()
# pli = ParseItems()
# pli.convert_raw_remittance(ais_doc, ais)
