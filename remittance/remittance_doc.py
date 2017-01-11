class RemittanceDoc():
    """This a holder for the raw incoming text document eg the text contents of the pdf.  It also provides a
    placedholder to add additional information about the document.
    Eg there may be multiple pages.
    this needs parsing and converting to a Remittance which will be the job of a specific parser.
    """

    def __init__(self):
        self.numpages = 1
        self.source_filename = ''
        self.source_file_path = ''  # this should not include the source file name

    def __repr__(self):
        return repr(self.page)

    def __str__(self):
        try:
            s = '#Page\n'
            for l in self.page:
                s += l + '\n'
        except AttributeError:
            s = '#No pages assigned yet'
        return s
