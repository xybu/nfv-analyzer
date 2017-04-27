def excel_style(row, col):
    """
    Convert given row and column number to an Excel-style cell name.
    http://code.activestate.com/recipes/578941-spread-sheet-style-column-enumeration-letter-to-nu/
    """
    quot, rem = divmod(col-1, 26)
    return((chr(quot-1 + ord('A')) if quot else '') +
           (chr(rem + ord('A')) + str(row)))
