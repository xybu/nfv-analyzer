"""
Parser of sysmon.py.

@author Xiangyu Bu <bu1@purdue.edu>
"""

from . import csv2xlsx


class NetStatCollection(csv2xlsx.BaseCsvCollection):
    def __init__(self, name):
        super().__init__(name, 'netstat')


class NetStatParser(csv2xlsx.BaseCsvParser):
    pass


class SysStatCollection(csv2xlsx.BaseCsvCollection):
    def __init__(self, name):
        super().__init__(name, 'sysstat')


class SysStatParser(csv2xlsx.BaseCsvParser):
    pass


class PsStatCollection(csv2xlsx.BaseCsvCollection):
    def __init__(self, name):
        super().__init__(name, 'psstat')


class PsStatParser(csv2xlsx.BaseCsvParser):
    pass
