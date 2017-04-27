#!/usr/bin/python3

# suricata_test.py
# Suricata tester.
#
# @author   Xiangyu Bu <bu1@purdue.edu>

import concurrent.futures
import logging
import os
import random
import signal
import spur
import subprocess
import sys
import time

from . import suricata_base


class SuricataTest(suricata_base.SuritacaTestBase):

    def __init__(self, remote_host, remote_user, remote_nics, local_tmpdir, remote_tmpdir, data_repo,
                 swappiness=5, stat_delay_sec=1, enable_suricata=True, suricata_config_file='suricata.yaml', suricata_runmode='workers',
                 iperf_instances=2, iperf_server_args=(), iperf_client_args=(), suricata_wrapper_cmd=(),
                 test_method='iperf', tcpreplay_tracefile=None):
        super().__init__(remote_host, remote_user, local_tmpdir, remote_tmpdir, data_repo)
        self.adjust_swappiness(swappiness)
        self.stat_delay_sec = stat_delay_sec
        self.suricata_config_file = suricata_config_file
        self.suricata_wrapper_cmd = suricata_wrapper_cmd
        self.suricata_runmode = suricata_runmode
        self.iperf_instances = iperf_instances
        self.iperf_server_args = list(iperf_server_args)
        self.iperf_client_args = list(iperf_client_args)
        self.remote_nics = remote_nics
        self.enable_suricata = enable_suricata
        self.test_method = test_method
        self.tcpreplay_tracefile = tcpreplay_tracefile

    def pre_cleanup(self):
        self.simple_call(['sudo', 'pkill', '-9', 'iperf3'])
        self.simple_call(['sudo', 'pkill', '-15', 'resmon'])
        self.simple_call(['sudo', 'pkill', '-9', 'Suricata-Main'])
        subprocess.call(['sudo', 'pkill', '-9', 'iperf3'])
        subprocess.call(['sudo', 'pkill', '-9', 'tcpreplay'])

    def post_cleanup(self):
        self.close()

    def test_iperf(self):
        logging.info('Running iperf servers.')
        iperf_server_procs = []
        # For each NIC, create iperf_instances iperf servers.
        for remote_nic in self.remote_nics:
            i = 0
            while i < self.iperf_instances:
                port = random.randrange(35201, 52500)
                cmd = ['iperf3', '-J', '--bind', remote_nic.ip, '-p', str(port), '-s',
                       '--logfile', os.path.join(self.remote_tmpdir, 'iperf_server_%s_%d.json' % (remote_nic.nic, port))] + self.iperf_server_args
                p = self.shell.spawn(cmd,
                                     cwd=self.remote_tmpdir,
                                     store_pid=True, allow_error=True)
                time.sleep(1)
                if p.is_running():
                    iperf_server_procs.append((remote_nic, port, p))
                    i = i + 1
                else:
                    logging.error('Iperf server is not running!')
        logging.info('Running iperf client.')
        all_clients = dict()
        result = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(iperf_server_procs)) as executor:
            for (remote_nic, port, _) in iperf_server_procs:
                cmd = ['iperf3', '-J', '-p', str(port), '-c', remote_nic.ip,
                       '--logfile', os.path.join(self.local_tmpdir, 'iperf_client_%s_%d.json' % (remote_nic.nic, port))] + self.iperf_client_args
                f = executor.submit(subprocess.call, cmd)
                all_clients[f] = (remote_nic.ip, port)
            for future in concurrent.futures.as_completed(all_clients):
                ip, port = all_clients[future]
                try:
                    retval = future.result()
                    result += retval
                    logging.info('Iperf client to %s:%d returned %d.\n' % (ip, port, retval))
                except Exception as e:
                    logging.error('Iperf client to %s:%d gives exception %s.\n' % (ip, port, e))
        logging.info('Iperf client finished.')

        logging.info('Terminating iperf server.')
        self.simple_call(['sudo', 'pkill', '-9', 'iperf3'])
        logging.info('Iperf server is supposedly killed.')
        return result

    def test_tcpreplay(self):
        logging.info('Running tcpreplay.')
        iperf_server_procs = []
        all_clients = dict()
        result = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.remote_nics) * self.iperf_instances) as executor:
            # Assuming remote NIC has the same name as local NIC.
            for remote_nic in self.remote_nics:
                for i in range(0, self.iperf_instances):
                    cmd = ['sudo', 'tcpreplay', '-i', remote_nic.nic, '-q',
                           os.path.join(os.path.dirname(os.path.abspath(__file__)), self.tcpreplay_tracefile)]
                    f = executor.submit(subprocess.call, cmd)
                    all_clients[f] = (remote_nic.nic, i)
            for future in concurrent.futures.as_completed(all_clients):
                nic, inst = all_clients[future]
                try:
                    retval = future.result()
                    result += retval
                    logging.info('tcpreplay to %s:%d returned %d.\n' % (nic, inst, retval))
                except Exception as e:
                    logging.error('tcpreplay to %s:%d gives exception %s.\n' % (nic, inst, e))
        logging.info('Tcpreplay client finished.')
        return result

    def run(self):
        logging.info('Initialing NICs.')
        for remote_nic in self.remote_nics:
            self.setup_nic(remote_nic.nic, is_local=False)
        logging.info('Initializing temp directories.')
        self.delete_tmpdir()
        self.create_tmpdir()
        self.pre_cleanup()
        if self.enable_suricata:
            logging.info('Spawning resmon and suricata.')
            suricata_cmd = ['suricata', '-c', '/etc/suricata/%s' % self.suricata_config_file,
                            '-l', self.remote_tmpdir, '--runmode', self.suricata_runmode]
            for remote_nic in self.remote_nics:
                suricata_cmd.extend(['-i', remote_nic.nic])
            if self.suricata_wrapper_cmd is not None and len(self.suricata_wrapper_cmd):
                suricata_cmd = list(self.suricata_wrapper_cmd) + suricata_cmd
            logging.info('Suricata command: "%s"', ' '.join(suricata_cmd))
            self.sysmon_proc = self.shell.spawn(['sudo', 'resmon',
                                                 '--delay', str(self.stat_delay_sec),
                                                 '--outfile', 'sysstat.receiver.csv',
                                                 '--ps-cmd', '--ps-cmd-outfile', 'psstat.suricata.csv',
                                                 '--'] + suricata_cmd,
                                                 cwd=self.remote_tmpdir, store_pid=True, allow_error=True)
            self.wait_for_suricata()
        if self.test_method == 'iperf':
            test_result = self.test_iperf()
        elif self.test_method == 'tcpreplay':
            test_result = self.test_tcpreplay()
        if self.enable_suricata:
            self.sysmon_proc.send_signal(signal.SIGTERM)
            self.sysmon_proc.wait_for_result()
            subprocess.call(['ssh', '%s@%s' % (self.remote_user, self.remote_host), 'pkill', '-15', 'resmon'])
            while subprocess.call(['ssh', '%s@%s' % (self.remote_user, self.remote_host), 'ps', '-p', str(self.sysmon_proc.pid)]) == 0:
                logging.info('Waiting for 1 second for resmon to stop.')
                time.sleep(1)
        if test_result == 0:
            self.commit_local_dir(self.local_tmpdir, self.data_repo.repo_user, self.data_repo.repo_host, self.data_repo.repo_dir)
            self.commit_remote_dir(self.remote_tmpdir, self.data_repo.repo_user, self.data_repo.repo_host, self.data_repo.repo_dir)
            self.delete_tmpdir()
        self.post_cleanup()
