# Built-Ins
import datetime
import os
import sys
import traceback
import time
# Externals
from easysnmp import Session, snmp_get, snmp_set, snmp_walk
import subprocess
import telnetlib
# Internals
from pckping import pping
from process import process
from Reporter import Reporter
from Tools import ToolKit


class cmResetTelnet(process):
    cm_uptime = ".1.3.6.1.2.1.1.3.0"
    timeOut = 300
    def __init__(self, ppi, iterations):
            print("cmResetTelnet CTOR")
            process.__init__(self, ppi)
            self.ResetCLIRep = Reporter(ppi)
            self.ResetCLIRep.set_testCaseTitle("CM Reset by CLI Record")
            self.individualResults = {}
            self.rawTimes= []
            self.resultsList = []
            self.overallResults = {}
            self.startReport()
            self.Pass_Ct = 0
            self.Fail_Ct = 0
            self.iterations = iterations
            

    def execute(self, pp):
        passed = False
        for int in range (self.iterations):
            if not ToolKit.isModemOnline(self.pp):
                # modem not online - log results and bail
                self.individualResults['msg'] = "Cable modem is not connected or not online"
                self.individualResults['error'] = 1
                self.individualResults['time'] = 0
                self.resultsList.append(self.individualResults)
                self.overallResults['Avg_Time'] = self.getAvg()
                self.overallResults['Fastest_Time']= min(self.rawTimes)
                self.overallResults['Slowest_Time']= max(self.rawTimes)
                self.overallResults['Attempts'] = int
                self.overallResults['Successful'] = self.Pass_Ct
                self.wrapUpReport(False, "CM is not online")
                print("Cable modem is not connected or not online")
                return

        
            print("Iteration #" + str(int + 1) + " of " + str(self.iterations))
            # Connect
            try:
                cmtsIP = self.pp.get_cmts['cmtsIp']
                tn = telnetlib.Telnet(cmtsIP,timeout=3)
                time.sleep(.5)
                self.lastResponse = tn.read_very_eager().decode("ascii").upper()
            except Exception as xcp:
                # Failed due to telnet rejection
                self.telnetFail('Telnet Rejected', 2)
                continue

            # sign-on
            rez = self.signOn(tn)
            if rez != 'OK':
                # Failed due to sign-on rejection
                rez = 'Failed Telnet Sign-On with the following response => ' + str(rez)
                self.telnetFail(rez, 3, tn)
                continue

            # enable
            rez = self.enable(tn)
            if rez != 'OK':
                # Failed on enable command
                rez = 'CM Rejected Enable Command with the following response =>' + str(rez)
                self.telnetFail(rez, 4, tn)
                continue

            # reset modem
            rez = self.reset(tn)
            if rez != 'OK':
                # Failed on reset command
                rez = "CM Rejected Reset Command with the following response => " + str(rez)
                self.telnet(rez, 5, tn)
                continue

            #StartTimer
            startTime = time.time()

            # verify modem is down
            time.sleep(1)
            rez = self.verifyModemDown(tn)
            if rez != 'OK':
                # Modem is still online
                rez = "CM Failed to Reset - Continues to reply to uptime MIB"
                self.telnetFail(rez, 6, tn)
                continue

            # wait for modem to return to service
            rez = self.waitForRecovery()
            if rez!= 'OK':
                # Modem didn't recover in 5 minutes
                rez = "CM waitForRecovery Timed Out"
                self.telnetFail(rez, 7, tn)
                continue

            # calculate time
            DeltaTime = time.time() - startTime

            # log success
            self.individualResults['msg'] = "successfully timed Reset via CMTS CLI command"
            self.individualResults['error'] = '0' # no error
            self.individualResults['time'] = DeltaTime
            self.resultsList.append(self.individualResults)
            self.rawTimes.append(DeltaTime)

            # increment counter
            self.Pass_Ct +=1
            print("Iteration succeeded")           
            
            # cycle telnet
            self.elegantShutdown(tn)
            time.sleep(.5)

        # compute timed results
        if len(self.rawTimes) > 0:
            avg = self.getAvg()
            self.overallResults['Avg_Time'] = round(avg,2)
            self.overallResults['Fastest_Time']= round(min(self.rawTimes),2)
            self.overallResults['Slowest_Time']= round(max(self.rawTimes),2)
            if self.Pass_Ct > self.iterations/2:
                passed = True
        finValue = "Average Time to Reset => " + str(avg)
        self.overallResults['Attempts'] = self.iterations
        self.overallResults['Successful'] = self.Pass_Ct
        self.wrapUpReport(passed, finValue )


    def getAvg(self):
        list(filter(lambda a: a != 0, self.rawTimes))
        try:
            return sum(self.rawTimes)/len(self.rawTimes)
        except Exception as xcp:
            return 0


    def snmpGetWrapper(self, oids):
        try:
            session = Session(hostname= self.pp.get_cmip, community="public", version=2, timeout=1, retries=1, )
            return session.get(oids)
        except Exception as xcp:
            print(xcp)
            # print traceback.print_exc()
            return {'error': 1, 'msg': str(xcp)}


    def elegantShutdown(self, telnt):
        try:
            telnt.write(b"enable\n")
            time.sleep(.5)
        except Exception as xcp:
            i=3
        try:
            telnt.close()
        except Exception as xcp:
            i=3

    
    def telnetFail(self, res, err, tel=None):
        print("Iteration failed with error code " + str(err) + " => " + res)
        # log failure
        self.individualResults['msg'] = res
        self.individualResults['error'] = err
        self.individualResults['time'] = 0
        self.resultsList.append(self.individualResults)
        # increment counter
        self.Fail_Ct += 1 
        # cycle telnet
        if not tel is None:
            self.elegantShutdown(tel)
            time.sleep(.5)

    def waitForRecovery(self):
        startTime = time.time()
        inc = 0
        time.sleep(.5)
        while True:
            try:
                response = self.snmpGetWrapper(cmResetTelnet.cm_uptime)
                if 'dict' not in str(type(response)) and 'snmp' in str(type(response)):
                    return 'OK'
            except Exception as xcp:
                time.sleep(1)
            if  time.time() - startTime > cmResetTelnet.timeOut:
                return "Modem Failed to Return to Service"
     

    def verifyModemDown(self, telnt):
        time.sleep(1)
        try:
            response = self.snmpGetWrapper(cmResetTelnet.cm_uptime)
            respType = type(response)
            if 'dict'  in str(type(response)) and 'snmp' not in str(type(response)):
                return 'OK'
        except Exception as xcp:
            return 'OK'
        return 'Failed to Reset Modem'
    
    def reset(self, telnt):
        mac = self.pp.get_cmmac
        msg = 'clear cable modem ' + mac + ' reset\n'
        b = msg.encode()
        try:
            telnt.write(b)
            return 'OK'
        except Exception as xcp:
            return str(xcp)
        return 'Unk Cause - Reset Failed'
         

    def enable(self, telnt):
        try:
            telnt.write(b"enable\n")
            time.sleep(.5)
            self.lastResponse  = telnt.read_very_eager().decode("ascii")  
            # send reset     
            if '#' in self.lastResponse:
                return 'OK'
        except Exception as xcp:
            return str(xcp)
        return 'Enable Failed'


    def signOn(self, telnt):
        # sign-on
        if 'username' in self.lastResponse.lower():
            try:
                telnt.write(b"engine\n")
                time.sleep(.5)
                self.lastResponse  = telnt.read_very_eager().decode("ascii")
            except Exception as xcp:
                return str(xcp)
        if 'password' in self.lastResponse.lower():
            try:
                telnt.write(b"g01ng2w0rk\n")
                time.sleep(.5)
                self.lastResponse = telnt.read_very_eager().decode("ascii")
                return 'OK'
            except Exception as xcp:
                return str(xcp)
        return 'failed unknown reason'


    def wrapUpReport(self, verdict, reportValue):
        self.overallResults['cmip'] = self.pp.get_cmip
        self.ResetCLIRep.set_endDate()
        self.ResetCLIRep.set_endTime()
        self.ResetCLIRep.logger.debug(self.overallResults)
        self.ResetCLIRep.addLogs(self.overallResults)
        if verdict == True:
            self.ResetCLIRep.CountSuccess()
        else:
            self.ResetCLIRep.CountFailure()
        self.ResetCLIRep.report["TestCase"]["CM_Reset_CLI"] = reportValue
        print(self.ResetCLIRep.generateReport())


    def startReport(self):
        self.ResetCLIRep.iterate()
        self.ResetCLIRep.set_testCaseTitle("CM Reset by CLI Flag")
        self.ResetCLIRep.set_startDate()
        self.ResetCLIRep.set_startTime()
        self.ResetCLIRep.logger.debug("resetCLI")


if __name__== "__main__":  
    cmmac = '247f20ad9744'
    cmmac = '5cs571a57d901'
    cmmac = 'a08e780eb8d8'
    opp = pping(cmmac)
    ocm = cmResetTelnet(opp,10)
    ocm.execute(opp)
    print("-----------")
    print(ocm.overallResults)

     
