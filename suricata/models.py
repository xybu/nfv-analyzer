#!/usr/bin/python3


import collections


DataRepository = collections.namedtuple('DataRepository', ('repo_host', 'repo_user', 'repo_dir'))

ReceiverHost = collections.namedtuple('ReceiverHost', ('host', 'user', 'nic', 'tmpdir_root'))

SenderHost = collections.namedtuple('SenderHost', ('nic', 'tmpdir_root'))


