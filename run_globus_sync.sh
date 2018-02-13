#!/bin/bash

# This is an example shell script that will do a globus sync via the sync.py
# python script. It assumes that the "modules" system is present on the system
# and the anaconda/python3.6 module is available.

# NB: YOU MUST RUN THIS SCRIPT ONCE INTERACTIVELY IN ORDER TO AUTHENTICATE TO
# GLOBUS.

# Once you have run it interactively one time, it will store an access token in
# the file .globus-sync-data.json. That access token must be refreshed within
# 48 hours, so if you run this script via cron make sure to run it every day.

# Create your app at https://auth.globus.org/v2/web/developers
# be sure to check the "Native App" checkbox and set the redirect URL to
# https://auth.globus.org/v2/web/auth-code
GLOBUS_SYNC_CLIENT_ID = ad6382da-8ada-47e1-810b-d8010525688f

# This is the endpoint where data will be synced *from*.
# The value below is the Northwestern Quest endpoint.
SOURCE_ENDPOINT = d5990400-6d04-11e5-ba46-22000b92c6ec

# The path you want to sync on the source endpoint
SOURCE_PATH = /home/mtr932

# This is the endpoint where data will be synced *to*.
DESTINATION_ENDPOINT = bdf3cd60-e128-11e7-802b-0a208f818180

# The path on the destination endpoint where data should be synced to.
DESTINATION_PATH = /~/globus-sync-testing/

# Can be one of 'exists', 'size', 'mtime', 'timestamp', or 'checksum'
# See https://docs.globus.org/cli/reference/transfer/ for details
SYNC_TYPE = checksum

# A friendly name for the transfer, will be visible in the Globus web interface
TRANSFER_LABEL = "Globus Backup"

module load python/anaconda3.6
python sync.py --synctype $SYNC_TYPE --transfer-label "$TRANSFER_LABEL" $SOURCE_ENDPOINT $SOURCE_PATH $DESTINATION_ENDPOINT $DESTINATION_PATH

