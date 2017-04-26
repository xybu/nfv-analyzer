#!/usr/bin/python3

# test_base.py
# Base class for a tester.
# 
# @author Xiangyu Bu <bu1@purdue.edu>

import logging
import subprocess
import sys
import time

import spur


class TestBase:

    def __init__(self):
        pass

    @property
    def shell(self):
        return self._shell

    @shell.setter
    def shell(self, sh):
        self._shell = sh

    def simple_call(self, cmd):
        return self.simple_cmd(self.shell, cmd)

    def adjust_swappiness(self, swappiness):
        self.simple_call(['sudo', 'sysctl', '-w', 'vm.swappiness=' + str(swappiness)])
        self.simple_call(['sysctl', 'vm.swappiness'])

    def close(self):
        if hasattr(self, '_shell'):
            del self._shell

    def commit_local_dir(self, dir, remote_user, remote_host, remote_dir):
        subprocess.call(['rsync', '-zvrpE', dir, '%s@%s:%s/' % (remote_user, remote_host, remote_dir)])

    def commit_remote_dir(self, dir, remote_user, remote_host, remote_dir):
        self.simple_call(['rsync', '-zvrpE', dir, '%s@%s:%s/' % (remote_user, remote_host, remote_dir)])

    @classmethod
    def reboot_remote_host(cls, host, user, wait_sec=30):
        logging.info('Rebooting host "%s"...', host)
        subprocess.call(['ssh', '%s@%s' % (user, host), 'sudo', 'reboot'])
        retval = 1
        while retval != 0:
            logging.info('Wait %d seconds for remote host "%s" to start...', wait_sec, host)
            time.sleep(wait_sec)
            retval = subprocess.call(['ssh', '%s@%s' % (user, host), 'echo', 'Remote host is ready.'])

    @classmethod
    def get_remote_shell(cls, host, user):
        logging.info('Obtaining SSH to "%s@%s"...' % (user, host))
        return spur.SshShell(hostname=host, username=user,
                             missing_host_key=spur.ssh.MissingHostKey.accept,
                             load_system_host_keys=True, look_for_private_keys=True)

    @classmethod
    def simple_cmd(cls, shell, cmd):
        return shell.run(cmd, allow_error=True).return_code
