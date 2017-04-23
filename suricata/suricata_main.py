#!/usr/bin/python3




from . import models

swappiness = 10
data_repo = models.DataRepository(repo_host='cap08.cs.purdue.edu', repo_user='bu1', repo_dir='/scratch/bu1/mt')
receiver_host = models.ReceiverHost(host='ohio.cs.purdue.edu', user='bu1', nic='eth0', tmpdir_root='/tmp')
sender_host = models.SenderHost(nic='eth0', tmpdir_root='/tmp')


def main():
    pass


if __name__ == '__main__':
    main()
