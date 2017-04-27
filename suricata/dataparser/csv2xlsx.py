"""
Parser of a generic csv.

@author Xiangyu Bu <bu1@purdue.edu>
"""

import csv
import threading

import xlsxwriter

from . import excelhelper
from . import exceptions


class BaseCsvCollection:
    
    def __init__(self, name, suffix):
        self._lock = threading.Lock()
        self.name = name
        self.suffix = suffix
        self.all_data = dict()
        print('Created new netstat collection: "%s"' % name)

    def get_key(self, engine, ts, trace, nworker, args):
        return ts

    def add(self, key, data):
        self._lock.acquire()
        self.all_data[key] = data
        self._lock.release()

    def to_xlsx(self):
        with open('%s,%s.log' % (self.name, self.suffix), 'w') as f:
            print('Sample size: %d' % len(self.all_data), file=f)
            workbook = xlsxwriter.Workbook('%s,%s.xlsx' % (self.name, self.suffix), {'strings_to_numbers': True})
            summary_sheet = workbook.add_worksheet('Summary')
            sheet_names = []
            max_rowcount = 0
            max_colcount = 0
            for key in sorted(self.all_data.keys()):
                sheet_name = str(key)
                data = self.all_data[key]
                sheet = workbook.add_worksheet(sheet_name)
                sheet_names.append(sheet_name)
                print('Sheet name: %s' % sheet_name, file=f)
                print('  Records: %d' % len(data), file=f)
                if max_rowcount < len(data):
                    max_rowcount = len(data)
                for rowid, row in enumerate(data):
                    if max_colcount < len(row):
                        max_colcount = len(row)
                    for colid, col in enumerate(row):
                        sheet.write(rowid, colid, col)
            for i in range(max_colcount):
                summary_sheet.write(0, i, '=%s!%s' % (sheet_names[0], excelhelper.excel_style(1, i+1)))
                # summary_sheet.set_column('{0}:{0}'.format(chr(ord('A') + i)), 10)
            for i in range(1, max_rowcount+1):
                for j in range(max_colcount):
                    related_cells = []
                    for s in sheet_names:
                        related_cells.append('%s!%s' % (s, excelhelper.excel_style(i+1, j+1)))
                    # print(related_cells)
                    summary_sheet.write(i, j, '=MEDIAN(%s)' % ','.join(related_cells))
            workbook.close()
        print('Saved "%s,%s.xlsx"' % (self.name, self.suffix))


class BaseCsvParser:
    
    def __init__(self):
        pass

    def parse(self, path):
        """ CSV file is assumed to have header. """
        data = []
        with open(path, 'rU') as f:
            reader = csv.reader(f)
            try:
                data.append(next(reader))
            except StopIteration:
                raise exceptions.NoContentException('File "%s" is empty.' % path)
            # data.append(header)
            for row in reader:
                data.append(row)
        return data
