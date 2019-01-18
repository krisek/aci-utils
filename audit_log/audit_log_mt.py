#!/usr/bin/python
# multithreaded use of the audit_log_dog library 
# fill the list of fabrics before running it

import time
from time import sleep
import argparse
import threading

from audit_log_dog import audit_log_dog

#put here the list of fabrics you want to get audit logs from
fabrics = [ ... ]

watchdogs = dict()

def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Process args to set interface adminstate')
    parser.add_argument('-l', '--login', required=True, action='store',
                        help='login.json to use')
    parser.add_argument('-d', '--dest_dir', required=True, action='store',
                        help='destination directory for the audit logs')
    parser.add_argument('-t', '--from_ts', required=False, action='store',
                        help='from ts')


    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = GetArgs()

    while True:
        for fabric in fabrics:
            if (fabric in watchdogs and not watchdogs[fabric].is_alive()) or fabric not in watchdogs:
                watchdogs[fabric] = threading.Thread(target=audit_log_dog, name=fabric, args=(fabric, args.dest_dir, args.login, args.from_ts,) )
                watchdogs[fabric].start()
                print("%s: thread started" % (fabric))
        sleep(60)

