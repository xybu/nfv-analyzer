#!/usr/bin/python3

import concurrent.futures
from collections import namedtuple
import logging
import os
import random
import time

from . import models
from . import suricata_test

nrepeat = 2
swappiness = 5
iperf_duration_sec = 30
data_repo = models.DataRepository(repo_host='cap08', repo_user='bu1', repo_dir='/scratch/bu1/525')
receiver_host = models.ReceiverHost(host='ohio', alt_host='192.168.0.11', user='root', nic='enp5s0f3', tmpdir_root='/tmp')
sender_host = models.SenderHost(nic='enp5s0f3', tmpdir_root='/tmp')

SuricataTestCase = namedtuple('SuricataTestCase',
                              ('name',                  # Name of the test.
                               'stat_delay_sec',        # Interval between polling resource usage.
                               'suricata_config_file',  # Config file to run Suricata with.
                               'iperf_server_args',     # Command-line arguments for iperf server-side.
                               'iperf_client_args',     # Command-line arguments for iperf client-side.
                               'suricata_wrapper_cmd',  # Wrapper command to run Suricata (e.g., vtune).
                               ))

all_tests = []

# # For UDP.
# for l in (32, 64):
#     for suricata_conf in ('1c1d', '1c2d', '1c4d', '1c8d',
#                           '2c1d', '2c2d', '2c4d', '2c8d',
#                           '4c1d', '4c2d', '4c4d', '4c8d', '4c16d',
#                           '8c1d', '8c2d', '8c4d', '8c8d', '8c16d',
#                           '16c1d', '16c2d', '16c4d', '16c8d', '16c16d', '16c32d'):
#         for (bw, par) in (('2M', 128), ('4M', 64), ('4M', 128), ('8M', 64), ('8M', 128)):
#             port = random.randrange(35201, 35299)
#             all_tests.append(SuricataTestCase(name='%s_udp_bw%sx%d_t%ds_l%d' % (suricata_conf, bw, par, iperf_duration_sec, l), stat_delay_sec=2,
#                                               suricata_config_file='suricata_%s.yaml' % suricata_conf,
#                                               iperf_server_args=('-s', '--port', str(port), '--interval', '10'),
#                                               iperf_client_args=('-c', receiver_host.alt_host, '--port', str(port), '--bandwidth', bw, '--time', str(iperf_duration_sec), '--udp', '-l', str(l), '-P', str(par)),
#                                               suricata_wrapper_cmd=()))

# For TCP.
for l in (32, 64, 16):
    for suricata_conf in ('1c1d', '1c2d', '1c4d', '1c8d',
                          '2c1d', '2c2d', '2c4d', '2c8d',
                          '4c1d', '4c2d', '4c4d', '4c8d', '4c16d',
                          '8c1d', '8c2d', '8c4d', '8c8d', '8c16d',
                          '16c1d', '16c2d', '16c4d', '16c8d', '16c16d', '16c32d'):
        for (bw, par) in (('2M', 128), ('4M', 64), ('4M', 128), ('8M', 64), ('8M', 128), ('4M', 32)):
            port = random.randrange(35201, 35299)
            all_tests.append(SuricataTestCase(name='%s_tcp_bw%sx%d_t%ds_l%d' % (suricata_conf, bw, par, iperf_duration_sec, l), stat_delay_sec=2,
                                              suricata_config_file='suricata_%s.yaml' % suricata_conf,
                                              iperf_server_args=('-s', '--port', str(port), '--interval', '10'),
                                              iperf_client_args=('-c', receiver_host.alt_host, '--port', str(port), '--bandwidth', bw, '--time', str(iperf_duration_sec), '-l', str(l), '-P', str(par)),
                                              suricata_wrapper_cmd=()))


def runtest(testcase, iter_id):
    """
    :param SuricataTestCase testcase: 
    :return: 
    """
    logging.info('Start test case "%s" iteration %d.', testcase.name, iter_id)
    start_time = int(time.time())
    test_inst = testcase.name + '_' + str(iter_id) + '_' + str(start_time)
    local_tmpdir = os.path.join(sender_host.tmpdir_root, test_inst)
    remote_tmpdir = os.path.join(receiver_host.tmpdir_root, test_inst)
    repo_dir = os.path.join(data_repo.repo_dir, test_inst)
    iperf_server_args = list(testcase.iperf_server_args)
    iperf_server_args.extend(['-J', '--logfile', os.path.join(remote_tmpdir, 'iperf_server.json')])
    iperf_client_args = list(testcase.iperf_client_args)
    iperf_client_args.extend(['-J', '--logfile', os.path.join(local_tmpdir, 'iperf_client.json')])
    tester = suricata_test.SuricataTest(remote_host=receiver_host.host, remote_user=receiver_host.user,
                                        local_out_nic=sender_host.nic, remote_in_nic=receiver_host.nic,
                                        local_tmpdir=local_tmpdir, remote_tmpdir=remote_tmpdir,
                                        data_repo=data_repo._replace(),
                                        swappiness=swappiness,
                                        stat_delay_sec=testcase.stat_delay_sec,
                                        suricata_config_file=testcase.suricata_config_file,
                                        iperf_server_args=iperf_server_args, iperf_client_args=iperf_client_args)
    tester.run()
    logging.info('Completed test case "%s" iteration %d.', testcase.name, iter_id)


def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)-15s] %(levelname)s: %(threadName)s: %(message)s')
    for i in range(0, nrepeat):
        for t in all_tests:
            runtest(t, i)
        suricata_test.SuricataTest.reboot_remote_host(receiver_host.host, receiver_host.user)


if __name__ == '__main__':
    main()
