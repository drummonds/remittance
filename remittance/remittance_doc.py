from remittance import RemittanceException

class RemittanceDoc():
    """This a holder for the raw incoming text document eg the text contents of the pdf.  It also provides a
    placedholder to add additional information about the document.
    Eg there may be multiple pages.
    this needs parsing and converting to a Remittance which will be the job of a specific parser.

    Each page is an array of lines
    """

    def __init__(self):
        self.source_filename = ''
        self.source_file_path = ''  # this should not include the source file name

    def __repr__(self):
        try:
            s = '#Pages\n'
            for p in self.pages:
                for l in p:
                    s += l + '\n'
        except AttributeError:
            s = '#No pages assigned yet'
        return s

    def __str__(self):
        return self.__repr__()

    @property
    def numpages(self):
        try:
            return len(self.pages)
        except AttributeError:
            return 0

    @property
    def page(self):
        if len(self.pages) == 1:
            return self.pages[0]
        else:
            raise RemittanceException("Number of pages = {} should be 1 for this property".format(self.numpages))

    def append_page(self, text):
        """Add text which is assumed to be a single chunk of text to the document"""
        page = text.split('\n')
        try:
            self.pages.append(page)
        except AttributeError:
            self.pages = [page]

