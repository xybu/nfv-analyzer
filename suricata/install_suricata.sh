#!/bin/bash

# According to
# https://redmine.openinfosecfoundation.org/projects/suricata/wiki/Ubuntu_Installation

VER=3.2.1

sudo apt-get install -yq wget
sudo apt-get install -yq libpcre3 libpcre3-dbg libpcre3-dev \
build-essential make autoconf automake libtool libpcap-dev libnet1-dev \
libyaml-0-2 libyaml-dev zlib1g zlib1g-dev libmagic-dev libcap-ng-dev \
libjansson-dev pkg-config libgeoip-dev libnetfilter-queue-dev \
libnetfilter-queue-dev libnetfilter-queue1 libnfnetlink-dev libnfnetlink0

cd /tmp
wget http://downloads.suricata-ids.org/suricata-$VER.tar.gz
tar xvf suricata-$VER.tar.gz
cd suricata-$VER

./configure --enable-nfqueue --enable-unittests --enable-profiling --prefix=/usr --sysconfdir=/etc --localstatedir=/var
make -j2
sudo make install-full
sudo ldconfig

# Make log dir
sudo mkdir -p /var/log/suricata

# Get some rule set from Internet.
cd /tmp
wget http://rules.emergingthreats.net/open/suricata/emerging.rules.tar.gz
sudo tar xvf emerging.rules.tar.gz
sudo cp -vfpr ./rules/* /etc/suricata/rules/
sudo wget --no-parent -l1 -r --no-directories -P /etc/suricata/rules/ https://rules.emergingthreats.net/open/suricata/rules/

sudo chmod u+s /usr/bin/suricata
