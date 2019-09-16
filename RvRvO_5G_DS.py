
# Setting up the Pal
import sys
import requests
import json
import time
import csv
import datetime
import re
import os
import subprocess
sys.path.append('../')
import ipaddrsrc



UNSET           = "UNSET"
scriptName      = __file__
ip              = UNSET
radiosetup_url  = UNSET
radiostatus_url = UNSET
status_url      = UNSET
endpoint_url    = UNSET


REST_TIMEOUT    = 30


print (ipaddrsrc.pal51_wifi_ip)

dictofRadioSetupSTA = {
    "mode"               : "octopal",
    "radioMode"          : "station",
    "stationNum"         : 1,
    "staBridge"          : False,
    "interface"          : "ac",
    "channelWidth"       : -1,
    "cwm"		 : "",
    "primaryChannel"     : 0,
    "channelScanList"    : [0],
    "guardInterval"      : "short",
    "rate"               : -1,
    "streams"            : 4,
    "priority"           : "bestEffort",
    "ssid"               : ipaddrsrc.ssid5,
    "securityProtocol"   : "mixed",
    "password"           : ipaddrsrc.appassword5g,
    "ipMode"             : 0,
    "ipAddress"          : ipaddrsrc.pal51_wifi_ip,
    "subnetMask"         : "255.255.255.0",
    "enable_pbssid"      : False,
}

dictofStandby = {
    'mode':'standby'
}

#
# check response from response object
def checkResponse (resp):
    if(resp.ok):
        print ("    Successful")
    else:
        #If response code is not ok (200), print the resulting http error code with description
        resp.raise_for_status() 


#
# put the device in standby mode
def setStandby():
    print ("==========================")
    print ("Setting standby mode.....")
    myResponse = requests.put(radiosetup_url,json=dictofStandby,timeout=REST_TIMEOUT)
    checkResponse(myResponse)
    

#
# Run the specified test type
def runTest(type):
    # Start test sequence
    setStandby()

    print ("")
    print ("==========================")
    print ("Starting Radio mode.....")
    if type=="STA":
        myResponse = requests.put(radiosetup_url,json=dictofRadioSetupSTA,timeout=REST_TIMEOUT)
    elif type=="AP":
        myResponse = requests.put(radiosetup_url,json=dictofRadioSetupAP,timeout=REST_TIMEOUT)
    else:
        print ("Unknown run type: %") % type
        return

    print ("==========================")
    print ("Reading radiosetup.....")
    myResponse = requests.get(radiosetup_url,timeout=REST_TIMEOUT)
    checkResponse(myResponse)
    radiosetup = json.loads(myResponse.content)
    print ("radiosetup response JSON:")
    print (json.dumps(radiosetup, indent=4))


#
# This function implements a way to run a command on this local host.
def runCommand(command, suppressOutput=False, password=None, writeThis=None):
    # Grab the stdout, and stderr at the same time
    # print "run_command: %s" % command
    p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    if writeThis:
        p.stdin.write(writeThis)
    (output, err) = p.communicate()
    if (not suppressOutput) and output:
        print ("              output='%s'") % output

    # Wait for command to terminate. Get return returncode ## p_status = p.wait()
    return output


#
# Print simple help message, and exit.
#
#
# Read the parameter to get the IP address of the target device

ip = ipaddrsrc.pal51_stamgmt_ip
# Do some simple sanity checking, to make sure device is reachable
command = "ping -n 1 %s" % ip
output = runCommand(command, suppressOutput=True)


#
# Set access URLs
radiosetup_url  = "http://" + ip + "/api/radiosetup"
radiostatus_url = "http://" + ip + "/api/radiostatus"
status_url      = "http://" + ip + "/api/status"
stationlist_url = "http://" + ip + "/api/stationlist"
endpoint_url = "http://" + ip + "/api/radioendpointrestart"

##########################################################################################


ip = ipaddrsrc.pal51_stamgmt_ip
print (ip)
print ("Running STA Test:")
runTest("STA")


##########################################################################################################

######Running MERN

###########################################################################################################

print ("waiting for association")
time.sleep(30)

sys.path.append('../../')

from src.octobox import Octobox

octobox = Octobox(host= ipaddrsrc.server_mgmt_ip, port=8086)


testInput = {
    'name': 'RvRvO 5G DS',
    'model': '',
    'revision': '',
    'reportingInterval': 1.0,
    'testDuration': '30',
    'settlingTime': 5,
    'stepDuration': 25,
    'quadAttenStart': 0,
    'quadAttenStep': 3,
    'quadAttenStop': 45,
    'rvrMode': 'RvRvO'
}
octobox.throughputTest.delete(testInput)
test, errors = octobox.throughputTest.create(testInput)
testId = test['id']

config = {'address': ipaddrsrc.server_traffic_ip, 'address2': ipaddrsrc.pal51_wifi_ip, 'name': 'Traffic 1'}

fromObj = config['address']
toObj = config['address2']
tp = config['name']
from_, errors = octobox.endpoint.readByAddress(fromObj)
to_, errors = octobox.endpoint.readByAddress(toObj)

trafficPairInput = {
       'testId': testId,
        'name': tp,
        'from': from_['id'],
        'to': to_['id'],
        'active': True,
        'setMss': None,
        'window': '2M',
	'parallel':10
    }

octobox.trafficPair.create(trafficPairInput)


attenInput = {'address': ipaddrsrc.atten_pal51_ip, 'id': testId}

addr = ipaddrsrc.atten_pal51_ip
attenByAddr = {'address': addr}
atten, errors = octobox.attenuator.read(attenByAddr)


plInput = {'testId': testId, 'mode': 'dynamic','attenuator': atten['id'], 'start': 10, 'attenuation':{'value':0}}
plInput, errors = octobox.pathLoss.create(plInput)

turnAddr = ipaddrsrc.turntable_ip
ttbyaddr = {'address': turnAddr}
tt, errors = octobox.turntable.readByAddr(ttbyaddr)

rot = {'id':testId,
       'turntable':tt['id'],
       'start':0,
       'stop':360,
       'step':30,
       'trainingInterval':5}

updatedRotation, errors = octobox.rotation.create(rot)

octobox.throughputTest.start(testId)

isRunning = True
while isRunning:
        isRunning, errors = octobox.throughputTest.isTestRunning(test)
        if isRunning:
            print('RvRvO test is running')
        else:
            print('Test complete')
        time.sleep(1)

##Generate and save CSV file

newpath = r'../../../../Documents/regression_results/{}'.format(ipaddrsrc.dateofteststart) 
if not os.path.exists(newpath):
    os.makedirs(newpath)

csv, errors = octobox.throughputTest.getCSV(test)
csv_path = os.path.expandvars('{}/{}.{}'.format(newpath,datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),csv['csvFilename']))
print ("waiting 20 sec to generate csv file.......")
time.sleep(20)
csv_request = requests.get(csv['href'])
with open(csv_path, 'wb') as f:
	for chunk in csv_request.iter_content(chunk_size=1024):
		if chunk:
			f.write(chunk)

print ("csv file saved under Documents/regression_results/{}".format(ipaddrsrc.dateofteststart))







