#!/usr/bin/python3

import concurrent.futures
import csv
import os
import subprocess


os.chdir('525')


def collect_metrics(dirname):
    d = {
        'capture.kernel_packets': 0,
        'capture.kernel_drops': 0,
        'decoder.pkts': 0,
        'decoder.bytes': 0,
    }
    ps = {
        'avg_cpu': 0,
        'max_mem_rss': 0,
    }
    with open(os.path.join(dirname, 'stats.log'), 'r') as f:
        for line in f:
            for k in d.keys():
                if line.startswith(k):
                    v = line.split('|')[-1].strip()
                    d[k] = v
    i = 0
    with open(os.path.join(dirname, 'psstat.suricata.csv'), 'r') as f:
        rdr = csv.reader(f)
        for row in rdr:
            if row[0] == 'Timestamp':
                continue
            uptime = int(row[1].strip())
            if uptime < 8:
                continue
            ps['avg_cpu'] = ps['avg_cpu'] + float(row[2].strip())
            ps['max_mem_rss'] = max(ps['max_mem_rss'], float(row[7].strip()))
            i = i + 1
    ps['avg_cpu'] = int(ps['avg_cpu'] / i)
    return d, ps


all_tasks = dict()
header = ('nc', 'nd', 'runmode', 'nnics', 'ninst', 'capture_pkts', 'drop_pkts', 'decoder_pkts', 'decoder_bytes', 'avg_cpu', 'max_rss', 'i', 'timestamp', 'trace')
rows = []
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
    for d in os.listdir('.'):
        f = executor.submit(collect_metrics, d)
        all_tasks[f] = d
    for f in concurrent.futures.as_completed(all_tasks):
        # Folder name is like "2c4d_snort.log_workers_8_1nics_0_1493306210".
        dirname = all_tasks[f]
        conf, trace_file, runmode, ninstances, nnics, i, ts = dirname.split('_')
        # How many capturers.
        nc = int(conf.split('c', maxsplit=1)[0])
        nd = int(conf.split('c', maxsplit=1)[1][:-1])
        # How many parallel iperfs / tcpreplays to each NIC.
        ninstances = int(ninstances)
        # How many NICs are involved.
        nnics = int(nnics.split('n', maxsplit=1)[0])
        # Which run of the test case.
        i = int(i)
        # Timestamp of the test run.
        ts = int(ts)
        # Result
        d, ps = f.result()
        rows.append((nc, nd, runmode, nnics, ninstances,
                     d['capture.kernel_packets'], d['capture.kernel_drops'],
                     d['decoder.pkts'], d['decoder.bytes'],
                     ps['avg_cpu'], ps['max_mem_rss'],
                     i, ts, trace_file))

with open('../tcpreplay.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(sorted(rows))
