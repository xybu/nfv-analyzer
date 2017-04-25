#!/usr/bin/python3

from collections import namedtuple
import logging
import os
import time

from . import models
from . import suricata_test

swappiness = 10
data_repo = models.DataRepository(repo_host='cap08.cs.purdue.edu', repo_user='bu1', repo_dir='/scratch2/bu1')
receiver_host = models.ReceiverHost(host='192.168.0.13', user='bu1', nic='enp34s0', tmpdir_root='/tmp')
sender_host = models.SenderHost(nic='enp34s0', tmpdir_root='/tmp')

SuricataTestCase = namedtuple('SuricataTestCase',
                              ('name',                  # Name of the test.
                               'stat_delay_sec',        # Interval between polling resource usage.
                               'suricata_config_file',  # Config file to run Suricata with.
                               'iperf_server_args',     # Command-line arguments for iperf server-side.
                               'iperf_client_args'      # Command-line arguments for iperf client-side.
                               ))

all_tests = (
    SuricataTestCase(name='1worker_10M_30s', stat_delay_sec=1,
                     suricata_config_file='suricata.yaml',
                     iperf_server_args=('-s', '--port', '5201', '--interval', '10'),
                     iperf_client_args=('-c', receiver_host.host, '--port', '5201', '--bandwidth', '10M', '--time', '30')),
)


def runtest(testcase):
    """
    :param SuricataTestCase testcase: 
    :return: 
    """
    logging.info('Start test case "%s".', testcase.name)
    start_time = int(time.time())
    local_tmpdir = os.path.join(sender_host.tmpdir_root, str(start_time) + '_' + testcase.name)
    remote_tmpdir = os.path.join(receiver_host.tmpdir_root, str(start_time) + '_' + testcase.name)
    iperf_server_args = list(testcase.iperf_server_args)
    iperf_server_args.extend(['-J', '--logfile', os.path.join(remote_tmpdir, 'iperf_server.json')])
    iperf_client_args = list(testcase.iperf_client_args)
    iperf_client_args.extend(['-J', '--logfile', os.path.join(local_tmpdir, 'iperf_client.json')])
    tester = suricata_test.SuricataTest(remote_host=receiver_host.host, remote_user=receiver_host.user,
                                        local_out_nic=sender_host.nic, remote_in_nic=receiver_host.nic,
                                        local_tmpdir=local_tmpdir, remote_tmpdir=remote_tmpdir,
                                        data_repo=data_repo,
                                        stat_delay_sec=testcase.stat_delay_sec,
                                        suricata_config_file=testcase.suricata_config_file,
                                        iperf_server_args=iperf_server_args, iperf_client_args=iperf_client_args)
    tester.run()
    logging.info('Completed test case "%s".', testcase.name)


def main():
    for t in all_tests:
        runtest(t)


if __name__ == '__main__':
    main()
