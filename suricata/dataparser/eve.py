"""
Parser of Suricata eve.json.

It assumes eve.json contains only one run of Suricata. That is, the recorded uptime
increases as the file progresses.

@author Xiangyu Bu <bu1@purdue.edu>
"""

import json
import threading

import xlsxwriter

from . import excelhelper
from . import exceptions


EVE_STRUCTURE = {
    "uptime": "key",
    "capture": {
      "kernel_packets": "avg",
      "kernel_drops": "avg",
    },
    "decoder": {
      "pkts": "avg",
      "bytes": "avg",
    },
    "detect": {
      "alert": "avg",
    }
}


class EveCollection:

    def __init__(self, name):
        self._lock = threading.Lock()
        self.name = name
        self.all_data = dict()
        print('Created new eve collection: "%s"' % name)

    def get_key(self, engine, ts, trace, nworker, args):
        return ts

    def add(self, key, data):
        self._lock.acquire()
        self.all_data[key] = data
        self._lock.release()

    def to_xlsx(self):
        # TODO: Parse this from STRUCTURE.
        sheet_header = ['uptime', 'capture.kernel_packets', 'capture.kernel_drops', 'decoder.pkts', 'decoder.bytes', 'detect.alert']
        max_rowcount = 0
        max_colcount = len(sheet_header)
        with open('%s,eve.log' % self.name, 'w') as f:
            print('Sample size: %d' % len(self.all_data), file=f)
            workbook = xlsxwriter.Workbook('%s,eve.xlsx' % self.name, {'strings_to_numbers': True})
            summary_sheet = workbook.add_worksheet('Summary')
            sheet_names = []
            for eve_id in sorted(self.all_data.keys()):
                sheet_name = str(eve_id)
                sheet_names.append(sheet_name)
                eve_sheet = workbook.add_worksheet(sheet_name)
                eve_data = self.all_data[eve_id]
                for i, column_name in enumerate(sheet_header):
                    eve_sheet.write(0, i, column_name)
                    eve_sheet.set_column('{0}:{0}'.format(chr(ord('A') + i)), 15)
                print('Sheet name: %s' % eve_id, file=f)
                print('  Records: %d' % len(eve_data.keys()), file=f)
                if max_rowcount < len(eve_data):
                    max_rowcount = len(eve_data)
                for row, uptime in enumerate(sorted(eve_data.keys())):
                    eve_sheet.write(row+1, 0, uptime)
                    for col, column_name in enumerate(sheet_header[1:]):
                        eve_sheet.write(row+1, col+1, eve_data[uptime][column_name])
            for i, column_name in enumerate(sheet_header):
                summary_sheet.write(0, i, column_name)
                summary_sheet.set_column('{0}:{0}'.format(chr(ord('A') + i)), 15)
            for i in range(1, max_rowcount+1):
                for j in range(max_colcount):
                    related_cells = []
                    for s in sheet_names:
                        related_cells.append('%s!%s' % (s, excelhelper.excel_style(i+1, j+1)))
                    # print(related_cells)
                    summary_sheet.write(i, j, '=INT(MEDIAN(%s))' % ','.join(related_cells))
            workbook.close()
        print('Saved "%s,eve.xlsx"' % self.name)

class EveParser:

    def __init__(self):
        pass

    def parse_stat(self, d):
        data_key = None
        data_value = dict()
        for key, role in EVE_STRUCTURE.items():
            if role == 'key':
                data_key = d[key]
            elif isinstance(role, dict):
                for subkey, subrole in role.items():
                    data_value['%s.%s' % (key, subkey)] = d[key][subkey]
        return data_key, data_value

    def parse(self, eve_path):
        data = dict()
        with open(eve_path, 'r') as f:
            for line in f:
                if 'stats' in line:
                    ev = json.loads(line)
                    if ev['event_type'] == 'stats':
                        key, val = self.parse_stat(ev['stats'])
                        data[key] = val
        if len(data) == 0:
            raise exceptions.NoContentException('File "%s" has no stat record.' % eve_path)
        return data
