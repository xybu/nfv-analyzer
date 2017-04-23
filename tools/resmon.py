#!/usr/bin/python3

"""
resmon.py

Resource monitor monitors system wide resource usage and availability. This script assumes that the number
of CPU cores does not change throughout the course.

NIC monitor component monitors the speed, in terms of Bps and Pkts/sec, and error and drop counts, of the specified NICs.

Process monitor component monitors resource usage of of a process and all its children processes.

Example usage:

$ resmon -d 1 --ps-cmd -- sleep 30
$ resmon --nic eth0,eth1
$ resmon --ps-pids 1 2 3

@author	Xiangyu Bu <bu1@purdue.edu>
"""

import argparse
import os
import sched
import signal
import sys
import time
import psutil


class SystemMonitor:

    def __init__(self, outfile_name=None, flush=False):
        print('System monitor started.', file=sys.stderr)
        ncores = self.ncores = psutil.cpu_count()
        if outfile_name is None:
            self.outfile = sys.stdout
        else:
            self.outfile = open(outfile_name, 'w')
        self.flush = flush
        self.outfile.write(
            'Timestamp,  Uptime, NCPU, %CPU, ' + ', '.join(['%CPU' + str(i) for i in range(ncores)]) +
            ', %MEM, mem.total.KB, mem.used.KB, mem.avail.KB, mem.free.KB' +
            ', %SWAP, swap.total.KB, swap.used.KB, swap.free.KB' +
            ', io.read, io.write, io.read.KB, io.write.KB, io.read.ms, io.write.ms\n')
        self.prev_disk_stat = psutil.disk_io_counters()
        self.starttime = int(time.time())
        self.poll_stat()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not hasattr(self, 'closed'):
            self.close()

    def close(self):
        if self.outfile is not sys.stdout:
            self.outfile.close()
        self.closed = True
        print('System monitor closed.', file=sys.stderr)

    def poll_stat(self):
        timestamp = int(time.time())
        uptime = timestamp - self.starttime
        total_cpu_percent = psutil.cpu_percent(percpu=False)
        percpu_percent = psutil.cpu_percent(percpu=True)
        mem_stat = psutil.virtual_memory()
        swap_stat = psutil.swap_memory()
        disk_stat = psutil.disk_io_counters()

        line = str(timestamp) + ', ' + str(uptime) + ', ' + \
            str(self.ncores) + ', ' + str(total_cpu_percent*self.ncores) + ', '
        line += ', '.join([str(i) for i in percpu_percent])
        line += ', ' + str(mem_stat.percent) + ', ' + str(mem_stat.total >> 10) + ', ' + str(
            mem_stat.used >> 10) + ', ' + str(mem_stat.available >> 10) + ', ' + str(mem_stat.free >> 10)
        line += ', ' + str(swap_stat.percent) + ', ' + str(swap_stat.total >> 10) + \
            ', ' + str(swap_stat.used >> 10) + ', ' + str(swap_stat.free >> 10)
        line += ', ' + str(disk_stat.read_count - self.prev_disk_stat.read_count) + ', ' + str(disk_stat.write_count - self.prev_disk_stat.write_count) + \
                ', ' + str((disk_stat.read_bytes - self.prev_disk_stat.read_bytes) >> 10) + ', ' + str((disk_stat.write_bytes - self.prev_disk_stat.write_bytes) >> 10) + \
                ', ' + str(disk_stat.read_time - self.prev_disk_stat.read_time) + \
            ', ' + str(disk_stat.write_time - self.prev_disk_stat.write_time)

        self.outfile.write(line + '\n')
        if self.flush:
            self.outfile.flush()
        self.prev_disk_stat = disk_stat


class NetworkInterfaceMonitor:

    def __init__(self, outfile_pattern='netstat.{nic}.csv', nics=[], flush=False):
        print('NIC monitor started.', file=sys.stderr)
        all_nics = psutil.net_if_stats()
        self.nic_files = dict()
        self.flush = flush
        for nic_name in nics:
            nic_name = nic_name.strip()
            if nic_name not in all_nics:
                print('Error: NIC "%s" does not exist. Skip.' %
                      nic_name, file=sys.stderr)
            else:
                self.nic_files[nic_name] = self.create_new_logfile(
                    outfile_pattern, nic_name)
        if len(self.nic_files) == 0:
            raise ValueError('No NIC to monitor.')
        self.prev_stat = dict()
        for nic, stat in psutil.net_io_counters(pernic=True).items():
            if nic in self.nic_files:
                self.prev_stat[nic] = stat
        self.starttime = int(time.time())
        self.poll_stat()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not hasattr(self, 'closed'):
            self.close()

    def close(self):
        for f in self.nic_files.values():
            f.close()
        self.closed = True
        print('NIC monitor closed.', file=sys.stderr)

    def create_new_logfile(self, pattern, nic_name):
        f = open(pattern.format(nic=nic_name), 'w')
        f.write(
            'Timestamp,  Uptime, NIC, sent.B, recv.B, sent.pkts, recv.pkts, err.in, err.out, drop.in, drop.out\n')
        return f

    def poll_stat(self):
        timestamp = int(time.time())
        uptime = timestamp - self.starttime
        net_stat = psutil.net_io_counters(pernic=True)
        for nic, f in self.nic_files.items():
            stat = net_stat[nic]
            prevstat = self.prev_stat[nic]
            f.write(str(timestamp) + ', ' + str(uptime) + ', ' + nic + ', ' +
                    str(stat.bytes_sent-prevstat.bytes_sent) + ', ' + str(stat.bytes_recv-prevstat.bytes_recv) + ', ' +
                    str(stat.packets_sent-prevstat.packets_sent) + ', ' + str(stat.packets_recv-prevstat.packets_recv) + ', ' +
                    str(stat.errin-prevstat.errin) + ', ' + str(stat.errout-prevstat.errout) + ', ' + str(stat.dropin-prevstat.dropin) + ', ' + str(stat.dropout-prevstat.dropout) + '\n')
            if self.flush:
                f.flush()
        self.prev_stat = net_stat


class ProcessSetMonitor:

    BASE_STAT = {
        'io.read': 0,
        'io.write': 0,
        'io.read.KB': 0,
        'io.write.KB': 0,
        'mem.rss.KB': 0,
        '%CPU': 0,
        'nctxsw': 0,
        'nthreads': 0
    }

    KEYS = sorted(BASE_STAT.keys())

    def __init__(self, outfile_name, cmd=None, pids=None, flush=False):

        if cmd is None and pids is None:
            raise ValueError('ProcessSetMonitor needs either a command or a set of PIDs to start.')

        print('ProcessSet monitor started.', file=sys.stderr)

        if outfile_name is None:
            self.outfile = sys.stdout
        else:
            self.outfile = open(outfile_name, 'w')

        self._has_child = False
        if cmd is not None:
            self._has_child = True
            if isinstance(cmd, str) or len(cmd) == 1 and ' ' in cmd[0]:
                self._subp = psutil.Popen(cmd, shell=True)
            else:
                self._subp = psutil.Popen(cmd)
            print('Info: spawned process %d.' % self._subp.pid, file=sys.stderr)
            if pids is None:
                pids = set((self._subp.pid,))
            else:
                pids.add(self._subp.pid)
        
        self.pids = [psutil.Process(p) for p in pids]
        self.flush = flush
        self.outfile.write('Timestamp, Uptime, ' + ', '.join(self.KEYS) + '\n')
        self.starttime = int(time.time())
        self.poll_stat()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not hasattr(self, 'closed'):
            self.close()

    def close(self):
        if self._has_child:
            self._subp.terminate()
            self._subp.wait()
        if self.outfile is not sys.stdout:
            self.outfile.close()
        self.closed = True
        print('ProcessSet monitor closed.', file=sys.stderr)

    def _stat_proc(self, proc, stat, visited):
        """ Recursively stat a process and its child processes. """
        if proc.pid in visited:
            return
        visited.add(proc.pid)
        with proc.oneshot():
            try:
                cpu_percent = proc.cpu_percent(interval=None)
                mem_info = proc.memory_full_info()
                io = proc.io_counters()
                nctxsw = proc.num_ctx_switches()
                nctxsw = nctxsw.voluntary + nctxsw.involuntary
                nthreads = proc.num_threads()
            except:
                return
            stat['io.read'] += io.read_count
            stat['io.write'] += io.write_count
            stat['io.read.KB'] += io.read_bytes
            stat['io.write.KB'] += io.write_bytes
            stat['mem.rss.KB'] += mem_info.rss
            stat['nctxsw'] += nctxsw
            stat['nthreads'] += nthreads
            stat['%CPU'] += cpu_percent
        for c in proc.children():
            self._stat_proc(c, stat, visited)

    def poll_stat(self):
        visited = set()
        curr_stat = dict(self.BASE_STAT)
        timestamp = int(time.time())
        uptime = timestamp - self.starttime
        for proc in self.pids:
            if proc.pid not in visited:
                if not proc.is_running():
                    self.pids.remove(proc)
                    continue
                self._stat_proc(proc, curr_stat, visited)
        curr_stat['%CPU'] = round(curr_stat['%CPU'], 3)
        curr_stat['io.read.KB'] >>= 10
        curr_stat['io.write.KB'] >>= 10
        curr_stat['mem.rss.KB'] >>= 10
        line = str(timestamp) + ', ' + str(uptime) + ', ' + \
            ', '.join([str(curr_stat[k]) for k in self.KEYS]) + '\n'
        self.outfile.write(line)
        if self.flush:
            self.outfile.flush()


def chprio(prio):
    try:
        psutil.Process(os.getpid()).nice(prio)
    except:
        print('Warning: failed to elevate priority.', file=sys.stderr)


def sigterm(signum, frame):
    raise KeyboardInterrupt()


def main():
    parser = argparse.ArgumentParser(
        description='Monitor system-wide resource availability or '
                    'resource usage of target processes.')
    
    parser.add_argument('--delay', '-d',
                        type=int, default=1, help='Interval, in sec, to poll information.')
    parser.add_argument('--flush', '-f',
                        default=False, action='store_true',
                        help='If present, flush the output files after each line is written.')
    parser.add_argument('--outfile', '-o',
                        type=str, nargs='?', default=None,
                        required=False, help='Name of system monitor output file. If unset, print to stdout.')
    parser.add_argument('--nic', '-n',
                        type=str, nargs='?', default=None, required=False,
                        help='Specify particular NICs, separated by a comma, to monitor. Default is none.')
    parser.add_argument('--nic-outfile',
                        type=str, nargs='?', default='netstat.{nic}.csv',
                        help='Name of the NIC monitor output file. Use "{nic}" as placeholder for NIC name. Default: "netstat.{nic}.csv".')
    parser.add_argument('--ps-cmd',
                        default=False, action='store_true',
                        help='If present, fork a process to run the target command and monitor its resource usage.')
    parser.add_argument('--ps-pids',
                        type=int, nargs='*', help='Monitor the specified PIDs and their children.')
    parser.add_argument('--ps-cmd-outfile',
                        type=str, nargs='?', default='psstat_cmd.csv',
                        help='File to store process monitor output for the target command. Default: "psstat_cmd.csv".')
    parser.add_argument('--ps-pid-outfile',
                        type=str, nargs='?', default='psstat_pid.csv',
                        help='File to store process monitor output for the PIDs. Default: "psstat_pid.csv".')
    
    if '--' in sys.argv:
        # Parse the target command.
        pos = sys.argv.index('--')
        args = parser.parse_args(args=sys.argv[1:pos])
        if not args.ps_cmd:
            print('Warning: process monitor is not enabled but target command is provided. Enable it.', file=sys.stderr)
            args.ps_cmd = True
        ps_cmd = sys.argv[pos + 1 :]
    else:
        args = parser.parse_args()
        if args.ps_cmd:
            print('Warning: "--ps-cmd" is given but the command is missing. Disable it.', file=sys.stderr)
            args.ps_cmd = False
        ps_cmd = None

    signal.signal(signal.SIGTERM, sigterm)

    try:
        chprio(-20)
        scheduler = sched.scheduler(time.time, time.sleep)
        sm = SystemMonitor(args.outfile, args.flush)

        enable_nic_mon = args.nic is not None
        if enable_nic_mon:
            try:
                nm = NetworkInterfaceMonitor(
                    args.nic_outfile, args.nic.split(','), args.flush)
            except ValueError as e:
                print('Error: ' + str(e), file=sys.stderr)
                enable_nic_mon = False

        if args.ps_pids is not None:
            pm_pid = ProcessSetMonitor(
                        outfile_name=args.ps_pid_outfile, pids=args.ps_pids, 
                        flush=args.flush)

        if args.ps_cmd:
            pm_cmd = ProcessSetMonitor(
                        outfile_name=args.ps_cmd_outfile, cmd=ps_cmd, 
                        flush=args.flush)

        ts = time.time()
        while True:
            ts = ts + args.delay

            scheduler.enterabs(time=ts, priority=2,
                               action=SystemMonitor.poll_stat, argument=(sm,))
            
            if enable_nic_mon:
                scheduler.enterabs(time=ts, priority=1,
                                   action=NetworkInterfaceMonitor.poll_stat, argument=(nm,))

            if args.ps_pids is not None:
                scheduler.enterabs(time=ts, priority=0,
                                   action=ProcessSetMonitor.poll_stat, argument=(pm_pid,))

            if args.ps_cmd:
                scheduler.enterabs(time=ts, priority=0,
                                   action=ProcessSetMonitor.poll_stat, argument=(pm_cmd,))

            scheduler.run()

    except KeyboardInterrupt:
        sm.close()
        if enable_nic_mon:
            nm.close()
        if args.ps_pids is not None:
            pm_pid.close()
        if args.ps_cmd:
            pm_cmd.close()


if __name__ == '__main__':
    main()
