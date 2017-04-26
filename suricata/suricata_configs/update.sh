#!/bin/bash

rsync -zrvpE ./*.yaml root@ohio:/etc/suricata/
