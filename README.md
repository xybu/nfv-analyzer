A collection of scripts that benchmark the following VNFs:

 * Suricata

## Suricata

To run the script, three hosts are needed:

 * Receiver host: the host to run Suricata (and iperf server).
 * Sender host: the host to run the script and iperf client or TCPreplay.
 * Data host: the host to save all the collected data.

The user of receiver host must be able to sudo without password prompting.

Command:

```bash
python3 -m suricata.suricata_main
```
