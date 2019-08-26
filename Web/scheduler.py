#-*-coding:utf-8 -*- 
import os 
import json
import time
import mongodb
import requests
import copy
import random

from notify import create_group,delete_group,send_email,get_token,send_mail_by_scanID

try:
    ssoUrl = 'https://portal-sso' + app_env['application_uris'][0][app_env['application_uris'][0].find('.'):]
except Exception as err:
    print('error: {}'.format(str(err)))

def checkPassiveStatus(scanId):
    try:
        print("Add check passive scan threading...")
        scan_info = db.findScan(scanId)
        pscanId = scan_info['pscanId']
        payload = {'scanId':pscanId}
        while True:
            r = requests.get('http://127.0.0.1:5000/JSON/spider/view/status/',params=payload)   
            if r.status_code == 200:
                r = r.json()
                status = r['status']
                db.modifyExistInfo('pscanStatus',status,scanId)
              
            r_html = requests.get('http://127.0.0.1:5000/OTHER/core/other/htmlreport/')
            if r_html.status_code == 200:
                db.modifyExistHtml('html',r_html.content,scanId)

            #scan finish
            if status == '100':
                db.modifyExistInfo('status','3',scanId)
                send_mail_by_scanID(ssoUrl,scanId)
                break
            time.sleep(1)
    except Exception as err:
        print('error: {}'.format(str(err)))
        db.modifyExistInfo('status','4',scanId)
    


def checkActiveStatus(scanId,targetURL,arecurse,inScopeOnly,method,postData,contextId,alertThreshold,attackStrength):
    try:
        print("Add check full scan threading...")
        scan_info = db.findScan(scanId)
        pscanId = scan_info['pscanId']
        payload = {'scanId':pscanId}

        # check passive scan
        while True:
            r = requests.get('http://127.0.0.1:5000/JSON/spider/view/status/',params=payload)   
            if r.status_code == 200:
                r = r.json()
                status = r['status']
                db.modifyExistInfo('pscanStatus',status,scanId)
  
            r_html = requests.get('http://127.0.0.1:5000/OTHER/core/other/htmlreport/')
            if r_html.status_code == 200:
                db.modifyExistHtml('html',r_html.content,scanId)

            #scan finish
            if status == '100':
                break
            time.sleep(1)

        # start active scan

        scanPolicyName = 'custom'
        remove_payload = {'scanPolicyName':scanPolicyName}
        r_remove = requests.get('http://127.0.0.1:5000/JSON/ascan/action/removeScanPolicy/',params=remove_payload)
        if r_remove.status_code == 200 or r_remove.status_code == 400:
            payload = {'scanPolicyName':scanPolicyName,'alertThreshold':alertThreshold,'attackStrength':attackStrength}
            r = requests.get('http://127.0.0.1:5000/JSON/ascan/action/addScanPolicy',params=payload)
            if r.status_code == 200:


                payload = {'url' : targetURL,'inScopeOnly':inScopeOnly,'recurse':arecurse,'scanPolicyName':scanPolicyName,'method':method,'postData':postData,'contextId':contextId}
                r_ascan = requests.get('http://127.0.0.1:5000/JSON/ascan/action/scan/',params=payload)
                if r_ascan.status_code == 200:
                    r_ascan = r_ascan.json()
                    db.modifyExistInfo('ascanId',r_ascan['scan'],scanId)
                    db.modifyExistInfo('status','2',scanId)
                #fail
                else: 
                    db.modifyExistInfo('status','4',scanId)
            else:
                print('add policy error')
                db.modifyExistInfo('status','4',scanId)
        else:
            print('remove error')
            db.modifyExistInfo('status','4',scanId)



        # check active scan

        scan_info = db.findScan(scanId)
        ascanId = scan_info['ascanId']
        payload = {'scanId':ascanId}
        while True:
            r = requests.get('http://127.0.0.1:5000/JSON/ascan/view/status/',params=payload)   
            if r.status_code == 200:
                r = r.json()
                status = r['status']
                db.modifyExistInfo('ascanStatus',status,scanId)
  
            r_html = requests.get('http://127.0.0.1:5000/OTHER/core/other/htmlreport/')
            if r_html.status_code == 200:
                db.modifyExistHtml('html',r_html.content,scanId)

            #scan finish
            if status == '100':
                db.modifyExistInfo('status','3',scanId)
                send_mail_by_scanID(ssoUrl,scanId)
                break
            time.sleep(1)

    except Exception as err:
        print('error: {}'.format(str(err)))
        db.modifyExistInfo('status','4',scanId)




def scan():
    scans = db.readyScans()
    if len(scans) > 0 :
        nowtime = int(time.time())
        #earliest scan
        scan = scans[0]
        if nowtime > scan['timeStamp']:
            nowScan = db.listScanning()
            if nowScan == None:
                scanId = scan['scanId']
                if scan['scanOption'] == '0':
                    db.modifyExistInfo('status','1',scanId)
                elif scan['scanOption'] == '2':
                    db.modifyExistInfo('status','2',scanId)

                if scan['period'] != 0:
                    newScan = copy.deepcopy(scan)    
                    userId_new = newScan['userId']
                    scanId_new = str(random.randint(1000000,9999999))
                    newScan['timeStamp'] = newScan['timeStamp'] + newScan['period']
                    newScan['scanId'] = scanId_new
                    db.addScan(newScan)

                    html_info = {
                        "userId":userId_new,
                        "scanId":scanId_new,
                        "html":""
                    }
                    db.addHtml(html_info)


                try:
                    # Delete all previous datas on ZAP server                                                                                           
                    r_delete = requests.get('http://127.0.0.1:5000/JSON/core/action/deleteAllAlerts')
                    if r_delete.status_code == 200:

                        # Get params from user setting
                        scanOption = scan['scanOption']
                        targetURL = scan['targetURL']
                        precurse = scan['pscanInfo']['recurse']
                        subtreeOnly = scan['pscanInfo']['subtreeOnly']
                        maxChildren = scan['pscanInfo']['maxChildren']
                        contextName = scan['pscanInfo']['contextName']

                        payload = {'url': targetURL, 'maxChildren': maxChildren,'recurse':precurse,'contextName':contextName ,'subtreeOnly':subtreeOnly}
                        r_passive = requests.get('http://127.0.0.1:5000/JSON/spider/action/scan',params=payload)
                        if r_passive.status_code == 200:                            
                            r_passive = r_passive.json() 
                            pscanId = r_passive['scan']
                            db.modifyExistInfo('pscanId',pscanId,scanId)

                            #thread
                            if scanOption == '0':
                                checkPassiveStatus(scanId)
                            elif scanOption == '2':
                                arecurse = scan['ascanInfo']['recurse']
                                inScopeOnly = scan['ascanInfo']['inScopeOnly']
                                method = scan['ascanInfo']['method']
                                postData = scan['ascanInfo']['postData']
                                contextId = scan['ascanInfo']['contextId']
                                alertThreshold = scan['ascanInfo']['alertThreshold']
                                attackStrength = scan['ascanInfo']['attackStrength']
                                checkActiveStatus(scanId,targetURL,arecurse,inScopeOnly,method,postData,contextId,alertThreshold,attackStrength)
                        #fail
                        else: 
                            db.modifyExistInfo('status','4',scanId)
                    else:
                        db.modifyExistInfo('status','4',scanId)
                except Exception as err:
                    print('error: {}'.format(str(err)))
                    db.modifyExistInfo('status','4',scanId)
            
            
            else:
                print('someone is scanning')
                

    else:
        pass


if __name__ == '__main__':
    db = mongodb.mongoDB()
    db.deleteRunningScans() 
    #blocking method
    while True:
        scan()
        time.sleep(5)







