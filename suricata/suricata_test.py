#!/usr/bin/python3

# suricata_test.py
# Suricata tester.
#
# @author   Xiangyu Bu <bu1@purdue.edu>

import logging
import signal
import subprocess
import sys
import time

from . import suricata_base


class SuricataTest(suricata_base.SuritacaTestBase):

    def __init__(self, remote_host, remote_user, local_out_nic, remote_in_nic, local_tmpdir, remote_tmpdir, data_repo,
                 swappiness=5, stat_delay_sec=1, suricata_config_file='suricata.yaml', iperf_server_args=(), iperf_client_args=()):
        super().__init__(remote_host, remote_user, local_out_nic, remote_in_nic, local_tmpdir, remote_tmpdir, data_repo)
        self.adjust_swappiness(swappiness)
        self.stat_delay_sec = stat_delay_sec
        self.suricata_config_file = suricata_config_file
        # Better use -J --logfile to save output to file to reduce network overhead.
        self.iperf_server_cmd = ['iperf3'] + list(iperf_server_args)
        self.iperf_client_cmd = ['iperf3'] + list(iperf_client_args)

    def test_iperf(self):
        logging.info('Running iperf.')
        iperf_server_proc = self.shell.spawn(self.iperf_server_cmd,
                                             cwd=self.remote_tmpdir, store_pid=True, allow_error=True,
                                             stdout=sys.stdout.buffer, stderr=sys.stdout.buffer)
        time.sleep(2)
        retval = subprocess.call(self.iperf_client_cmd, cwd=self.local_tmpdir)
        if retval != 0:
            logging.error('iperf client exit with %d. Command: \"%s\".', retval, self.iperf_client_cmd)
        iperf_server_proc.terminate()
        iperf_server_proc.wait()
        return retval

    def run(self):
        logging.info('Initialing NICs.')
        self.setup_nics()
        logging.info('Initializing temp directories.')
        self.delete_tmpdir()
        self.create_tmpdir()
        logging.info('Spawning resmon and suricata.')
        self.sysmon_proc = self.shell.spawn(['sudo', 'resmon',
                                             '--delay', str(self.stat_delay_sec),
                                             '--outfile', 'sysstat.receiver.csv',
                                             '--nic', self.remote_in_nic, '--nic-outfile', 'netstat.{nic}.csv',
                                             '--ps-cmd', '--ps-cmd-outfile', 'psstat.suricata.csv',
                                             '--', 'suricata', '--af-packet=%s' % self.remote_in_nic,
                                             '-c', '/etc/suricata/%s' % self.suricata_config_file,
                                             '-l', self.remote_tmpdir],
                                            cwd=self.remote_tmpdir, store_pid=True, allow_error=True,
                                            stdout=sys.stdout.buffer, stderr=sys.stdout.buffer)
        self.wait_for_suricata()
        test_result = self.test_iperf()
        self.sysmon_proc.send_signal(signal.SIGTERM)
        self.sysmon_proc.wait_for_result()
        if test_result == 0:
            self.commit_local_dir(self.local_tmpdir, self.data_repo.repo_user, self.data_repo.repo_host, self.data_repo.repo_dir)
            self.commit_remote_dir(self.remote_tmpdir, self.data_repo.repo_user, self.data_repo.repo_host, self.data_repo.repo_dir)
            self.delete_tmpdir()
