#!/usr/bin/python3

# suricata_test.py
# Suricata tester.
#
# @author   Xiangyu Bu <bu1@purdue.edu>


from . import models
from . import suricata_base


class SuricataTest(suricata_base.SuritacaTestBase):

    def __init__(self, remote_host, remote_user, local_out_nic, remote_in_nic, local_tmpdir, remote_tmpdir, data_repo):
        super().__init__(remote_host, remote_user, local_out_nic, remote_in_nic, local_tmpdir, remote_tmpdir, data_repo)

    def run(self):
        self.setup_nics()
        self.delete_tmpdir()
        self.create_tmpdir()

