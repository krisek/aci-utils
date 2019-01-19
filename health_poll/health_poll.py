#!/usr/bin/python
import argparse
import requests
import json
import re
from dateutil.parser import *
from datetime import *
import calendar
import time
from datetime import datetime

from collections import defaultdict

import requests.packages.urllib3

requests.packages.urllib3.disable_warnings()

import socket

proxies = {
#  'http': '',
#  'https': '',
}

logintoken = '';

def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Retrieve metrics, health and fault information from APIC')
    parser.add_argument('-l', '--login', required=True, action='store',
                        help='login.json to use')
    parser.add_argument('-c', '--carbon-server', required=True, action='store',
                        help='carbon server address ')
    parser.add_argument('-p', '--carbon-port', required=False, action='store',
                        help='carbon server port (default: 2003)', default=2003)
    parser.add_argument('-d', '--carbon-destination', required=True, action='store',
                        help='carbon server server destination path (metrics location)')
    parser.add_argument('-f', '--fabric', required=True, action='store',
                        help='fabric to get information from')                       
    args = parser.parse_args()
    return args

def GetApicURL(apic_url):
    global total_downloaded, total_requests
    #print("request %s" % (apic_url))
    r = requests.get(apic_url , headers={'Content-type': 'application/json', 'Cookie': "APIC-cookie=%s" % (logintoken)}, verify=False, proxies=proxies)
    mo = json.loads(r.text)
    mo['tc'] = int(mo['totalCount'])
    return mo

args = {}

def main():
    """
    Go get args
    """
    global logintoken
    global args
    global proxies

    args = GetArgs()

    f = open(args.login)
    login_data = f.read()
    f.close()


    result = ""
    stat_text = ""
    apic = args.fabric
    carbon_destination = args.carbon_destination
    
    r = requests.post('https://'+ apic + '/api/aaaLogin.json', data = login_data, headers={'Content-type': 'application/json'}, verify=False, proxies=proxies)

    loginresult = json.loads(r.text)
    logintoken = loginresult['imdata'][0]['aaaLogin']['attributes']['token']

    health_info = GetApicURL('https://' + apic +'/api/node/mo/topology/health.json')
    try:
        stat_text += "{}.health {} {}".format(carbon_destination, health_info['imdata'][0]['fabricHealthTotal']['attributes']['cur'], parse(health_info['imdata'][0]['fabricHealthTotal']['attributes']['updTs']).strftime('%s')) + '\n'
    except:
        pass

    mos = ['topSystem','l3extInstP',  'l3extOut', 'fvTenant', 'fvCtx', 'fvBD', 'fvAp', 'fvAEPg']# ['fabricPod']

    for aci_object_class in mos:
        url = 'https://' + apic + '/api/node/class/' + aci_object_class + '.json'
        if(aci_object_class == 'fabricPod'):
            url += '?rsp-subtree-include=stats&rsp-subtree-class=fabricOverallHealthHist5min'
        else:
            url += '?rsp-subtree-include=stats,health&rsp-subtree-class=l2EgrPktsAg15min,l2IngrBytesAg15min'
        #l2EgrPktsAg15min
        #l2IngrBytesAg15min
        data = GetApicURL(url)
        
        if 'totalCount' in data and int(data['totalCount']) > 0 and 'imdata' in data:
            #take them one by one
            for aci_object in data['imdata']:
                #nested_dict = lambda: defaultdict(nested_dict)
                #stat = nested_dict()
                stat = defaultdict(dict)
                stat[u'apic'] = carbon_destination;
                stat[u'mo'] =  aci_object[aci_object_class]['attributes']['dn'].replace('/','.');
                stat[u'metrics'] = {}
                stat[u'metrics'][u'health'] = {'value': 'n/a', 'ts': 'n/a'}
                sub = ''
                if('children' not in aci_object[aci_object_class]):
                    continue
                for subtree_child in aci_object[aci_object_class]['children']:
                    if('healthInst' in subtree_child):
                        stat[u'metrics'][u'health'] = {'value': subtree_child['healthInst']['attributes']['cur'],
                                                        'ts': parse(subtree_child['healthInst']['attributes']['updTs']).strftime('%s')}

                    if('l2IngrBytesAg15min' in subtree_child):
                        sub = 'igress';
                        field = 'l2IngrBytesAg15min';

                    if('l2EgrPktsAg15min' in subtree_child):
                        sub = 'egress';
                        field = 'l2EgrPktsAg15min'

                    if('l2IngrBytesAg15min' in subtree_child or 'l2EgrPktsAg15min' in subtree_child):
                        if('attributes' in subtree_child[field]):
                            metrics_base = subtree_child[field]['attributes']
                        else:
                            metrics_base = {}
                            print("No metrics received %s" % (stat[u'mo']))
                        ts = parse(metrics_base['repIntvEnd']).strftime('%s')
                        for metric in metrics_base:
                            matchObj = re.search(r'drop|flood|multicast|unicast', metric, re.M|re.I)
                            if matchObj:
                                try:
                                    if(metrics_base[metric] != ''):
                                        stat[u'metrics'][sub+'.'+metric] = {'value': metrics_base[metric], 'ts': ts}
                                except:
                                    pass
                            else:
                                continue

                for metric in stat[u'metrics']:
                    stat_text += "%s.%s.%s %s %s\n" % (stat['apic'], stat['mo'], metric, stat[u'metrics'][metric]['value'], stat[u'metrics'][metric]['ts'])
                    
    faultQuery = 'https://' + apic + '/api/node/class/faultInfo.json?query-target-filter=and(ne(faultInfo.severity,"cleared"))'
    faultData = GetApicURL(faultQuery)
    faults = dict()
    if  'totalCount' in faultData and int(faultData['totalCount']) > 0 and 'imdata' in faultData:
    	for faultInfo in faultData['imdata']:
           for faultInfo_type in faultInfo:
                #print(faultInfo[faultInfo_type]['attributes']['dn'])
                matchObj = re.match( r'^([^\/]+)\/([^\/]+)\/([^\/]+)', faultInfo[faultInfo_type]['attributes']['dn'], re.M|re.I) 
                fault_loc = carbon_destination
                if matchObj:
                    if matchObj.group(1) == 'uni':
                        fault_loc = fault_loc + '.' + matchObj.group(1) + '.' + matchObj.group(2)
                    else:
                        fault_loc = fault_loc + '.' + matchObj.group(1) + '.' + matchObj.group(2) + '.' +  matchObj.group(3)
                else:
                    next
                fault_loc = fault_loc + '.faults'
                for attr in ['domain', 'type', 'subject', 'severity', 'cause', 'lc', 'code']:
                    key = faultInfo[faultInfo_type]['attributes'].setdefault(attr, 'unknown')
                    fault_loc = fault_loc + '.' + key
                #print(fault_loc)
                if fault_loc not in faults:
                    faults[fault_loc] = 0
                faults[fault_loc] = faults[fault_loc] + 1
    ts = calendar.timegm(time.gmtime()) 
    for fault_loc in faults:
    	stat_text += "%s %s %s\n" % (fault_loc, faults[fault_loc], ts) 

    #send data to carbon server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (args.carbon_server, args.carbon_port)
    sock.connect(server_address)
    sock.sendall(stat_text)
    sock.close

# Start program
if __name__ == "__main__":
  main()
