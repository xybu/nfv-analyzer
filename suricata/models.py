#!/usr/bin/python3


import collections


DataRepository = collections.namedtuple('DataRepository', ('repo_host', 'repo_user', 'repo_dir'))

ReceiverHost = collections.namedtuple('ReceiverHost', ('host', 'user', 'tmpdir_root'))

SenderHost = collections.namedtuple('SenderHost', ('tmpdir_root'))

RemoteNic = collections.namedtuple('RemoteNic', ('nic', 'ip'))
