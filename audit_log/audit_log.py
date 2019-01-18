#!/usr/bin/python
# simple use of the audit_log_dog library 

import time
from time import sleep
import argparse
import threading

from audit_log_dog import audit_log_dog

def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Process args to set interface adminstate')
    parser.add_argument('-l', '--login', required=True, action='store',
                        help='login.json to use')
    parser.add_argument('-f', '--fabric', required=True, action='store',
                        help='fabric to get audit logs from')                       
    parser.add_argument('-d', '--dest_dir', required=True, action='store',
                        help='destination directory for the audit logs')
    parser.add_argument('-t', '--from_ts', required=False, action='store',
                        help='from ts')


    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = GetArgs()
    audit_log_dog(args.fabric, args.dest_dir, args.login, args.from_ts)