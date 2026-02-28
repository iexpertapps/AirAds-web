#!/bin/bash
cd /Users/syedsmacbook/Developer/AirAds-web/airaad/backend
python3 seed_master.py > /tmp/seed_out.txt 2>&1
echo "Exit: $?" >> /tmp/seed_out.txt
