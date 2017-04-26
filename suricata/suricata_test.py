#!/usr/bin/python3

# suricata_test.py
# Suricata tester.
#
# @author   Xiangyu Bu <bu1@purdue.edu>

import logging
import os
import signal
import spur
import subprocess
import sys
import time

from . import suricata_base


class SuricataTest(suricata_base.SuritacaTestBase):

    def __init__(self, remote_host, remote_user, local_out_nic, remote_in_nic, local_tmpdir, remote_tmpdir, data_repo,
                 swappiness=5, stat_delay_sec=1, suricata_config_file='suricata.yaml',
                 iperf_server_args=(), iperf_client_args=(), suricata_wrapper_cmd=()):
        super().__init__(remote_host, remote_user, local_out_nic, remote_in_nic, local_tmpdir, remote_tmpdir, data_repo)
        self.adjust_swappiness(swappiness)
        self.stat_delay_sec = stat_delay_sec
        self.suricata_config_file = suricata_config_file
        self.suricata_wrapper_cmd = suricata_wrapper_cmd
        # Better use -J --logfile to save output to file to reduce network overhead.
        self.iperf_server_cmd = ['iperf3'] + list(iperf_server_args)
        self.iperf_client_cmd = ['iperf3'] + list(iperf_client_args)

    def pre_cleanup(self):
        self.simple_call(['sudo', 'pkill', '-9', 'iperf3'])
        self.simple_call(['sudo', 'pkill', '-15', 'resmon'])
        self.simple_call(['sudo', 'pkill', '-9', 'Suricata-Main'])
        subprocess.call(['sudo', 'pkill', '-9', 'iperf3'])

    def post_cleanup(self):
        self.close()

    def test_iperf(self):
        logging.info('Running iperf.')
        iperf_server_proc = self.shell.spawn(self.iperf_server_cmd,
                                             cwd=self.remote_tmpdir,
                                             store_pid=True, allow_error=True)
        time.sleep(2)
        if not iperf_server_proc.is_running():
            logging.error('Iperf server is not running!')
            return -1
        logging.info('Running iperf client.')
        retval = subprocess.call(self.iperf_client_cmd, cwd=self.local_tmpdir)
        logging.info('Iperf client finished.')
        if retval != 0:
            logging.error('iperf client exit with %d. Command: \"%s\".', retval, self.iperf_client_cmd)
        logging.info('Terminating iperf server.')
        self.simple_call(['sudo', 'pkill', '-9', 'iperf3'])
        logging.info('Iperf server is supposedly killed.')
        # try:
        #     iperf_server_proc.send_signal(signal.SIGTERM)
        # except:
        #     pass
        # try:
        #     iperf_server_proc.wait_for_result()
        # except spur.spur.RunProcessError as e:
        #     if e.return_code == 1: return retval
        return retval

    def run(self):
        logging.info('Initialing NICs.')
        self.setup_nics()
        logging.info('Initializing temp directories.')
        self.delete_tmpdir()
        self.create_tmpdir()
        self.pre_cleanup()
        logging.info('Spawning resmon and suricata.')
        suricata_cmd = ['suricata', '--af-packet=%s' % self.remote_in_nic,
                        '-c', '/etc/suricata/%s' % self.suricata_config_file,
                        '-l', self.remote_tmpdir]
        if self.suricata_wrapper_cmd is not None and len(self.suricata_wrapper_cmd):
            suricata_cmd = list(self.suricata_wrapper_cmd) + suricata_cmd
        self.sysmon_proc = self.shell.spawn(['sudo', 'resmon',
                                             '--delay', str(self.stat_delay_sec),
                                             '--outfile', 'sysstat.receiver.csv',
                                             '--nic', self.remote_in_nic, '--nic-outfile', 'netstat.{nic}.csv',
                                             '--ps-cmd', '--ps-cmd-outfile', 'psstat.suricata.csv',
                                             '--'] + suricata_cmd,
                                             cwd=self.remote_tmpdir, store_pid=True, allow_error=True)
        self.wait_for_suricata()
        test_result = self.test_iperf()
        # self.sysmon_proc.send_signal(signal.SIGTERM)
        # self.sysmon_proc.wait_for_result()
        subprocess.call(['ssh', '%s@%s' % (self.remote_user, self.remote_host), 'pkill', '-15', 'resmon'])
        while subprocess.call(['ssh', '%s@%s' % (self.remote_user, self.remote_host), 'ps', '-p', str(self.sysmon_proc.pid)]) == 0:
            logging.info('Waiting for 1 second for resmon to stop.')
            time.sleep(1)
        if test_result == 0:
            self.commit_local_dir(self.local_tmpdir, self.data_repo.repo_user, self.data_repo.repo_host, self.data_repo.repo_dir)
            self.commit_remote_dir(self.remote_tmpdir, self.data_repo.repo_user, self.data_repo.repo_host, self.data_repo.repo_dir)
            self.delete_tmpdir()
        self.post_cleanup()
