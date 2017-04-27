#!/usr/bin/python3

from collections import namedtuple
import logging
import os
import time

from . import models
from . import suricata_test

nrepeat = 1
swappiness = 5
iperf_duration_sec = 30

data_repo = models.DataRepository(repo_host='cap08',
                                  repo_user='bu1',
                                  repo_dir='/scratch/bu1/525')

receiver_host = models.ReceiverHost(host='ohio',
                                    user='root',
                                    tmpdir_root='/tmp')

sender_host = models.SenderHost(tmpdir_root='/tmp')

all_receiver_nics = (
  models.RemoteNic(nic='enp5s0f1', ip='192.168.0.15'),
  models.RemoteNic(nic='enp5s0f2', ip='192.168.0.13'),
  models.RemoteNic(nic='enp5s0f3', ip='192.168.0.11'),
)

SuricataTestCase = namedtuple('SuricataTestCase',
                              ('name',                  # Name of the test.
                               'stat_delay_sec',        # Interval between polling resource usage.
                               'suricata_config_file',  # Config file to run Suricata with.
                               'enable_suricata',       # Spawn Suricata in the test.
                               'iperf_nics',            # A set of NICs to use for iperf server.
                               'iperf_instances',       # Number of iperf pairs to run.
                               'iperf_server_args',     # Command-line arguments for iperf server-side.
                               'iperf_client_args',     # Command-line arguments for iperf client-side.
                               'suricata_wrapper_cmd',  # Wrapper command to run Suricata (e.g., vtune).
                               'suricata_runmode',      # Runmode of Suricata. Either workers (default) or autofp.
                               'test_method',           # Either "tcpreplay" or "iperf".
                               'tcpreplay_tracefile'    # Trace file for tcpreplay.
                               ))

all_tests = []

# We are sending (bw x par x iperf_instances bits/sec) / (1 bytes/pkt) = pkts / sec. 
# It is pkt/second that matters, not MBps.

# for recv_nics in (all_receiver_nics[:1], all_receiver_nics[:3]):
#     # For each of the two thread models.
#     for (suricata_runmode, conf_suffix) in (('autofp', '_af'), ('workers', '')):
#         # For UDP.
#         for l in (512, ):
#             for suricata_conf in ('1c1d', # '1c2d', '1c4d', '1c8d',
#                                   '2c2d', #'2c1d', '2c2d', '2c4d', '2c8d',
#                                   '4c4d', #'4c1d', '4c2d', '4c4d', '4c8d', '4c16d',
#                                   #'8c1d', '8c2d', '8c4d', '8c8d', '8c16d',
#                                   #'16c1d', '16c2d', '16c4d', '16c8d', '16c16d', '16c32d'):
#                                   ):
#                 for (bw, par) in (('4M', 40),):
#                     t = SuricataTestCase(name='%s_udp_bw%sx%dx1_t%ds_l%d_%s_%dnic' % (suricata_conf, bw, par, iperf_duration_sec, l, suricata_runmode, len(recv_nics)), stat_delay_sec=2,
#                                          suricata_config_file='suricata_%s.yaml' % (suricata_conf + conf_suffix),
#                                          iperf_nics=recv_nics,
#                                          # We need more than one instance only when CPU usage of iperf process reaches 100%.
#                                          iperf_instances=1,
#                                          iperf_server_args=('-i', '10', '-1'),
#                                          iperf_client_args=('-i', '10', '-w', '64K', '-Z',
#                                                             '--bandwidth', bw, '--time', str(iperf_duration_sec), '--udp', '-l', str(l), '-P', str(par)),
#                                          enable_suricata=True,
#                                          suricata_runmode=suricata_runmode,
#                                          suricata_wrapper_cmd=())
#                     all_tests.append(t)
#                     all_tests.append(t._replace(enable_suricata=False, name=t.name + '_base'))
#all_tests.append(None) # Reboot.
    # For TCP.
    
    #all_tests.append(None) # Reboot.


# for recv_nics in (all_receiver_nics[:1], all_receiver_nics[:3]):
#     # For each of the two thread models.
#     for (suricata_runmode, conf_suffix) in (('autofp', '_af'), ('workers', '')):
#         # For TCP.
#         for l in (128, ):
#             for suricata_conf in ('1c1d', '1c2d',# '1c4d', '1c8d',
#                                   '2c2d', '2c1d',# '2c2d', '2c4d', '2c8d',
#                                   '4c4d', '4c1d', '4c2d', #'4c4d', '4c8d', '4c16d',
#                                   #'8c1d', '8c2d', '8c4d', '8c8d', '8c16d',
#                                   #'16c1d', '16c2d', '16c4d', '16c8d', '16c16d', '16c32d'):
#                                   ):
#                 for (bw, par) in (('4M', 40),):
#                     t = SuricataTestCase(name='%s_tcp_bw%sx%dx1_t%ds_l%d_%s_%dnic' % (suricata_conf, bw, par, iperf_duration_sec, l, suricata_runmode, len(recv_nics)), stat_delay_sec=2,
#                                          suricata_config_file='suricata_%s.yaml' % (suricata_conf + conf_suffix),
#                                          iperf_nics=recv_nics,
#                                          # We need more than one instance only when CPU usage of iperf process reaches 100%.
#                                          iperf_instances=1,
#                                          iperf_server_args=('-i', '20', '-1'),
#                                          iperf_client_args=('-i', '20', '-Z', '-w', 
#                                                             '--bandwidth', bw, '--time', str(iperf_duration_sec), '-l', str(l), '-P', str(par)),
#                                          enable_suricata=True,
#                                          suricata_runmode=suricata_runmode,
#                                          suricata_wrapper_cmd=())
#                     all_tests.append(t)
                    # all_tests.append(t._replace(enable_suricata=False, name=t.name + '_base'))

# all_tests.append(None) # Reboot.

# for recv_nics in (all_receiver_nics[:1],):
#     # For each of the two thread models.
#     for (suricata_runmode, conf_suffix) in (('autofp', '_af'), ('workers', '')):
#         for suricata_conf in ('1c1d', '1c2d', '1c4d', #'1c8d',
#                               '2c1d', '2c2d', '2c4d', '2c8d',
#                               '4c1d', '4c2d', '4c4d', '4c8d', '4c16d',
#                               '8c1d', '8c2d', '8c4d', '8c8d', '8c16d',
#                               '16c16d', '16c32d'):
#             for num_instances in (16, 8, 4):
#                 t = SuricataTestCase(name='%s_snort.log_%s_%d_%dnics' % (suricata_conf, suricata_runmode, num_instances, len(recv_nics)), stat_delay_sec=2,
#                                      suricata_config_file='suricata_%s.yaml' % (suricata_conf + conf_suffix),
#                                      iperf_nics=recv_nics,
#                                      # We need more than one instance only when CPU usage of iperf process reaches 100%.
#                                      iperf_instances=num_instances,
#                                      iperf_server_args=(),
#                                      iperf_client_args=(),
#                                      test_method='tcpreplay',
#                                      tcpreplay_tracefile='traces/snort.log.1425823194',
#                                      enable_suricata=True,
#                                      suricata_runmode=suricata_runmode,
#                                      suricata_wrapper_cmd=())
#                 all_tests.append(t)

all_tests.append(None) # Reboot.

for recv_nics in (all_receiver_nics[:2],):
    # For each of the two thread models.
    # for (suricata_runmode, conf_suffix) in (('autofp', '_af'), ('workers', '')):
    for (suricata_runmode, conf_suffix) in (('workers', ''),):
        for suricata_conf in (#'1c1d', '1c2d', '1c4d',
                              #'2c1d', '2c2d', '2c4d',
                              #'4c1d', '4c2d', '4c4d', '4c8d',
                              '8c1d', '8c2d', '8c4d', '8c8d', '8c16d'):
            for num_instances in (8, 4):
                t = SuricataTestCase(name='%s_snort.log_%s_%d_%dnics' % (suricata_conf, suricata_runmode, num_instances, len(recv_nics)), stat_delay_sec=2,
                                     suricata_config_file='suricata_%s.yaml' % (suricata_conf + conf_suffix),
                                     iperf_nics=recv_nics,
                                     # We need more than one instance only when CPU usage of iperf process reaches 100%.
                                     iperf_instances=num_instances,
                                     iperf_server_args=(),
                                     iperf_client_args=(),
                                     test_method='tcpreplay',
                                     tcpreplay_tracefile='traces/snort.log.1425823194',
                                     enable_suricata=True,
                                     suricata_runmode=suricata_runmode,
                                     suricata_wrapper_cmd=())
                all_tests.append(t)


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
    tester = suricata_test.SuricataTest(remote_host=receiver_host.host,
                                        remote_user=receiver_host.user,
                                        remote_nics=testcase.iperf_nics,
                                        local_tmpdir=local_tmpdir,
                                        remote_tmpdir=remote_tmpdir,
                                        data_repo=data_repo._replace(),
                                        swappiness=swappiness,
                                        stat_delay_sec=testcase.stat_delay_sec,
                                        enable_suricata=testcase.enable_suricata,
                                        suricata_config_file=testcase.suricata_config_file,
                                        suricata_runmode=testcase.suricata_runmode,
                                        iperf_instances=testcase.iperf_instances,
                                        iperf_server_args=testcase.iperf_server_args,
                                        iperf_client_args=testcase.iperf_client_args,
                                        test_method=testcase.test_method,
                                        tcpreplay_tracefile=testcase.tcpreplay_tracefile)
    tester.run()
    logging.info('Completed test case "%s" iteration %d.', testcase.name, iter_id)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)-15s] %(levelname)s: %(threadName)s: %(message)s')
    for i in range(0, nrepeat):
        for t in all_tests:
            if t is None:
                suricata_test.SuricataTest.reboot_remote_host(receiver_host.host, receiver_host.user)
            else:
                runtest(t, i)


if __name__ == '__main__':
    main()
