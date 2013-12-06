#!/usr/bin/env bash

# Ensure our net interface is up
sleep 20

echo "*** Updating Package Listings ***"
sudo apt-get update

echo "*** Upgrading Base System ***"
sudo apt-get -y upgrade

echo "*** Installing Packages ***"
sudo apt-get install -y build-essential python-pip

echo "*** Install Python Packages ***"
sudo pip install -r /var/autoroute/requirements.txt

echo "*** Configure Autoroute ***"
sudo chmod +x /var/autoroute/autoroute.py
sudo cp /var/autoroute/packer/autoroute.conf /etc/init/autoroute.conf

# Configure logging
sudo tee "/etc/cloud/cloud.cfg.d/99-autoroute.cfg" > /dev/null << "EOF"
#cloud-config
output: {all: '| tee -a /var/log/cloud-init-output.log'}
EOF
