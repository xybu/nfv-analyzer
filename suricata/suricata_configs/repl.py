#!/usr/bin/python3

import os

with open('suricata_template.yaml', 'r') as f:
    data = f.read()

for (c, d) in ((1, 1), (1, 2), (1, 4), (1, 8),
               (2, 1), (2, 2), (2, 4), (2, 8),
               (4, 1), (4, 2), (4, 4), (4, 8), (4, 16),
               (8, 1), (8, 2), (8, 4), (8, 8), (8, 16),
               (16, 1), (16, 2), (16, 4), (16, 8), (16, 16), (16, 32)):
    content = data
    content = content.replace('<AF_PACKET_THREADS>', str(c))
    content = content.replace('<PCAP_THREADS>', str(c))
    content = content.replace('<WORKER_THREADS>', str(d))
    with open('suricata_%dc%dd.yaml' % (c, d), 'w') as f:
        content2 = content.replace('<ENABLE_CPU_AFFINITY>', 'no', 1)
        f.write(content2)
    with open('suricata_%dc%dd_af.yaml' % (c, d), 'w') as f:
        content3 = content.replace('<ENABLE_CPU_AFFINITY>', 'yes', 1)
        f.write(content3)
