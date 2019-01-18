#!/usr/bin/python

import requests
from requests.packages import urllib3

from lomond import WebSocket
from lomond.persist import persist
import ssl
import json
from textwrap import dedent
import time
from time import sleep

from pprint import pprint
import re
from datetime import datetime

urllib3.disable_warnings()

websockets = dict();
not_connected = dict()
apic_events = dict()


proxies = {
#  'https': 'http://',
#  'http': 'http://',
}

def audit_log_dog(apic_address, dest_dir, login='~/.login.json' , from_ts = 0, ):

    debug=False
    not_connected[apic_address] = 0

    if from_ts == None:
        from_ts = 0

    if from_ts != 0:
        not_connected[apic_address] = from_ts

    def log(message):
        print(apic_address + ": " + message)


    def init():
        log("audit_log_dog init called apic: %s, from_ts: %s, not_connected: %s" % (apic_address, from_ts, not_connected[apic_address]))

        login_failure = True;
        wait = 5
        if(not_connected[apic_address] == 0 and from_ts == 0):
            not_connected[apic_address] = time.time()
        if(not_connected[apic_address] == 0 and from_ts != 0):
            not_connected[apic_address] = from_ts

        while login_failure:
            try:
                f = open(login)
                login_data = f.read()
                f.close()
                log("connecting")
                r = requests.post('https://' + apic_address + '/api/aaaLogin.json', data = login_data, headers={'Content-type': 'application/json'}, verify=False, proxies=proxies)
                loginresult = json.loads(r.text)
                logintoken = loginresult['imdata'][0]['aaaLogin']['attributes']['token']
                log("logintoken: %s" % (logintoken))
                login_failure = False
            except:
                sleep(wait)
                if(wait < 120):
                    wait += 10

        poll(logintoken)


    def dump_message(message):

        if apic_address not in apic_events:
            apic_events[apic_address] = list()

        message['apic'] = apic_address

        if message['id'] not in apic_events[apic_address]:

            print("{apic}\t{created}\t{descr}\t{affected}\t{user}\t{ind}".format(**message))

            f = open(dest_dir + '/audit.'+ apic_address + '.json.log'  , 'a')
            f.write(message['created'] + "\t"+ json.dumps(message) + "\n")
            f.close()

            f = open(dest_dir + '/audit.'+ apic_address + '.log'  , 'a')
            f.write("{apic}\t{created}\t{descr}\t{affected}\t{user}\t{ind}\n".format(**message))
            f.close()

            apic_events[apic_address].append(message["id"])
        else:
            print("message {id} already logged, not writing to file again; {apic}\t{created}\t{descr}\t{affected}\t{user}\t{ind}".format(**message))


    def poll(logintoken):

        websocket = WebSocket("wss://{apic_address}/socket{token}".format(apic_address=apic_address, token=logintoken))

        subscribed = False
        count = 0;

        for event in persist(websocket):
            if event.name not in ['poll', 'pong']:
                log("event received " + event.name)

            count += 1

            if event.name in ['ready', 'poll', 'pong'] and (not subscribed or count > 20):
                #2019-01-10T00:14:24
                from_time = datetime.fromtimestamp(int(not_connected[apic_address])).strftime('%Y-%m-%dT%H:%M:%S')
                #from_time = datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%dT%H:%M:%S')

                log("subscribing from %s" % (from_time))
                r = requests.get('https://' + apic_address + "/api/node/class/aaaModLR.json?subscription=yes&page=0&page-size=10000&query-target-filter=and(gt(aaaModLR.created,\"%s\"))" % (from_time), headers={'Content-type': 'application/json', 'Cookie': "APIC-cookie=%s" % (logintoken)}, verify=False, proxies=proxies)
                log("subscribe request returned (%s)" % (r.status_code))
                result = json.loads(r.text)
                #dump previus events
                for aci_event in result.setdefault("imdata", []):
                    if "aaaModLR" in aci_event:
                        message = aci_event["aaaModLR"]["attributes"]
                        dump_message(message)


                count = 0
                if r.ok:
                    subscribed = True
                    log("subscribed")
                    #we won't ever need events before this
                    not_connected[apic_address] = time.time()
                else:
                    log(r.text)
                    result = json.loads(r.text)
                    subscribed = False
                    log("not subscribed (request was not ok)")
                    if(re.match(r'Token was invalid', result["imdata"][0]["error"]["attributes"]["text"])):
                        log("Token was invalid; reconnecting")
                        break

            if event.name == 'text':
                #websocket.send_text(event.text)
                aci_event = json.loads(event.text)
                message = aci_event["imdata"][0]["aaaModLR"]["attributes"]
                dump_message(message)
                #we won't ever need events before this
                not_connected[apic_address] = time.time()

        websocket.close()
        init()


    init()

