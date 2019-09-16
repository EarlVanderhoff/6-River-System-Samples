# Built-Ins
import datetime
import os
import sys
import traceback

# Externals
from easysnmp import Session, snmp_get
import netsnmp
import subprocess

# Internals
from pckping import pping
from process import process
from Reporter import Reporter
from Tools import ToolKit

# Externals
from easysnmp import Session, snmp_get
import netsnmp
import subprocess

import time
import timeout_decorator
#from wrapt_timeout_decorator import *


class cmBPIState(process):
    docsBpi2CmAuthState ='.1.3.6.1.2.1.126.1.1.1.1.3.2'
    #docsBpi2CmAuthState ='.1.3.6.1.2.1.126.1.1.1.1.3.21'
    def __init__(self, ppi):
            process.__init__(self, ppi)
            print("cmBPIState CTOR")
            self.authvalue = ""
            self.BPIAuthRecRep = Reporter(ppi)
            #self.BPIAuthRecRep.set_testCaseTitle("CM BPI Authorization State Record")
            self.results = {}
            self.startReport()
            

    def snmpGetWrapper(self, host, oids):
            try:
                session = Session(hostname=host, community="public", version=2, timeout=1, retries=1)
                return session.get(oids)

            except Exception as xcp:
                print(xcp)
                return {'error': 1, 'msg': str(xcp)}

    
    #@timeout(0.4, use_signals=False)
    def execute(self):
        ret = {}
        if ToolKit.isModemOnline(self.pp):

            __ = self.snmpGetWrapper(cmBPIState.docsBpi2CmAuthState)

            if 'dict' not in str(type(__)) and 'snmp' in str(type(__)):
                try:
                    ret = __.value
                    if 'NOSUCHINSTANCE' in ret:
                        self.authvalue = "NOSUCHINSTANCE"
                        self.results['cmip'] = self.pp.get_cmip
                        self.results['error'] = 3
                        self.results['msg'] = "BPI Authorization Error => Unable to Identify MIB: {0}".format(ret['msg'])
                        self.wrapUpReport(False, self.authvalue)
                    elif 'NOSUCHOBJECT' in ret:
                        self.authvalue = "NOSUCHOBJECT"
                        self.results['cmip'] = self.pp.get_cmip
                        self.results['error'] = 4
                        self.results['msg'] = "BPI Authorization Error => Unable to Identify CM: {0}".format(ret['msg'])
                        self.wrapUpReport(False, self.authvalue)
                    else: # Success
                        possible_values =  {1:'start', 2:'authWait', 3:'authorized', 4:'reauthWait', 5:'authRejectWait', 6:'silent'}
                        self.authvalue = possible_values[int(ret)]
                        self.results['cmip'] = self.pp.get_cmip
                        self.results['msg'] = "BPI Authorization Successfully Read"
                        self.wrapUpReport(True, self.authvalue)


                except Exception as xcp:
                    print(xcp)
                    print(traceback.print_exc())
                    self.wrapUpReport(True, self.authvalue)
            else:
                self.authvalue = 'unk error'
                self.results['cmip'] = self.pp.get_cmip
                self.results['error'] = 1
                self.results['msg'] = "Error in get BPI Authorization State: {0}".format(ret['msg'])
                self.wrapUpReport(False, self.authvalue)
        else:
            self.authvalue = 'cm not found'
            self.results['error'] = 1
            self.results['msg'] = "Cable modem is not connected or not online, please check"
            self.wrapUpReport(False, self.authvalue)
            print(" MAC DOES NOT EXIST IN THE DB")
            print(self.results)  


    def snmpGetWrapper(self, oids):
        try:
            session = Session(hostname= self.pp.get_cmip, community="public", version=2, timeout=5, retries=1)
            return session.get(oids)
        except Exception as xcp:
            print(xcp)
            return {'error': 1, 'msg': str(xcp)}      


    def wrapUpReport(self, verdict, sysAuthValue):
            self.BPIAuthRecRep.set_endDate()
            self.BPIAuthRecRep.set_endTime()
            self.BPIAuthRecRep.logger.debug(self.results)
            self.BPIAuthRecRep.addLogs(self.results)
            if verdict == True:
                self.BPIAuthRecRep.CountSuccess()
            else:
                self.BPIAuthRecRep.CountFailure()
            self.BPIAuthRecRep.report["TestCase"]["BPIAuth_State"] = sysAuthValue
            print(self.BPIAuthRecRep.generateReport())


    def startReport(self):
        self.BPIAuthRecRep.iterate()
        self.BPIAuthRecRep.set_testCaseTitle("CM BPI Authorization Flag")
        self.BPIAuthRecRep.set_startDate()
        self.BPIAuthRecRep.set_startTime()
        self.BPIAuthRecRep.logger.debug("bpi")



if __name__== "__main__":  
     cmmac = '247f20ad9744'
     #cmmac = '5cs571a57d901'
     #cmmac = '5cs571a57d901'

     #cmmac = '5cs571a57d901'

     opp = pping(cmmac)
     ocm = cmBPIState(opp)
     ocm.execute()
     print("-----------")
     print(ocm.authvalue)

     
