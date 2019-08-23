#-*-coding:utf-8 -*-
import time
import random
import os
from flask import Flask,request,redirect
from flask import jsonify,abort,Response, make_response
from flask_cors import cross_origin
import requests
import json
import zipfile,io
import subprocess

from functools import wraps
from datetime import datetime
import base64
import random
import time
import calendar
import mongodb
import threading
db = mongodb.mongoDB()

app = Flask(__name__,static_url_path='',root_path=os.getcwd())    

import create_datasource
from datasource_route import app
from dashboard import datasource_init, create_dashboard, delete_dashboard
from report import process_report
from notify import create_group,delete_group,send_email,get_token,send_mail_by_scanID
#apiURL='https://dashboard-grafana-1-3-2.arfa.wise-paas.com'
apiURL=''
ssoUrl = ''
appURL = ''
checkPassiveStatusThread = ''
checkActiveStatusThread = ''
try:
    app_env = json.loads(os.environ['VCAP_APPLICATION'])
    ssoUrl = 'https://portal-sso' + app_env['application_uris'][0][app_env['application_uris'][0].find('.'):]
    appURL = 'https://'+app_env['application_uris'][0]
    print('get environment variables!')
except Exception as err:
    print('Can not get environment variables:{}'.format(str(err)))
    ssoUrl = 'https://portal-sso.arfa.wise-paas.com'
    appURL = 'https://zap-security-0816.arfa.wise-paas.com'
domainName = ssoUrl[ssoUrl.find('.'):]

#decorator
def EIToken_verification(func):
    @wraps(func)
    def warp(*args, **kwargs):
        global ssoUrl
        EIToken =request.cookies.get('EIToken')
        res=requests.get(ssoUrl + "/v2.0/users/me",cookies={'EIToken': EIToken})    
        if res.status_code == 200:
            return func(*args, **kwargs)
        else:
            return abort(401)
    return warp

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
            else:
                print('add policy error')
        else:
            print('remove error')



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

def getUserIdFromToken(EIToken):
    info = EIToken.split('.')[1]
    lenx = len(info)%4
    if lenx == 1:
        info += '==='
    if lenx == 2:
        info += '=='
    if lenx == 3:
        info += '='
    userId = json.loads(base64.b64decode(info))['userId']
    userName =  json.loads(base64.b64decode(info))['firstName'] +" "+  json.loads(base64.b64decode(info))['lastName']  
    return userId,userName

@app.route('/')
def home():
    return app.send_static_file('home.html')

@app.route('/doc')
def doc():
    return app.send_static_file('doc.html')

@app.route('/deleteScans',methods=['POST'])
@EIToken_verification
def deleteScans():
    EIToken = request.cookies.get('EIToken')
    userId,userName = getUserIdFromToken(EIToken)
    scanIdArr = request.form.getlist('scanIdArr[]')
    for scanId in scanIdArr:
        scan = db.findScan(scanId)
        if scan != None:
            status = scan['status']
            scan_userId = scan['userId']
            if userId == scan_userId:
                if status == '3' or status == '0':
                    db.deleteScan(scanId)
                    delete_dashboard(appURL,apiURL,scanId, EIToken)
    return jsonify({'Result':'OK'})

@app.route('/dashboardLink',methods=['GET'])
@EIToken_verification
def dashboardLInk():
    scanId =request.cookies.get('scanId')
    scan = db.findScan(scanId)
    url = scan['dashboardLInk']
    if url == None:
        abort(500)
    else:
        return url

@app.route('/finishStatus',methods=['GET'])
@EIToken_verification
def finishStatus():
    scanId = request.cookies.get('scanId')
    db.modifyExistInfo('status','3',scanId)
    return 'OK' 

@app.route('/updateHtml',methods=['GET'])
@EIToken_verification
def updateHtml():
    scanId = request.cookies.get('scanId')      
    r = requests.get('http://127.0.0.1:5000/OTHER/core/other/htmlreport/')
    if r.status_code == 200:
        db.modifyExistHtml('html',r.content,scanId)
        return jsonify({'Result':'OK'})
    else:
        abort(500)

@app.route('/downloadHtml',methods=['GET'])
@cross_origin()
def downloadHtml():
    try:
        scanId = request.args.get('scanId')
        html_info = db.findHtml(scanId)
        if html_info == None:
            return 'fail'
        else:
            html= html_info['html']
            html= process_report(html)
            #response = make_response(html,200)
            #response.headers['Content-Type'] = 'application/html'
            #response.headers['Content-Disposition'] = 'attachment; filename={}'.format('scan_report.html')
            #return response
            return html
    except Exception as err:
        print('download_file error: {}'.format(str(err)))
        abort(500)

@app.route('/waitScan',methods=['GET'])
@EIToken_verification
def waitScan():
    scanId = request.cookies.get('scanId')
    scan = db.listScanning()
    if scan == None:
        result = jsonify({"Result":"NEEDWAITING"})
        return result
    elif scan['scanId'] == scanId:
        result = jsonify({"Result":"SCANNING"})
        return result
    else:
        abort(500)

@app.route('/Scan',methods=['GET'])
@EIToken_verification
def Scan():
    
    #Necessary setting
    scanOption = request.args.get('scanOption')
    targetURL = request.args.get('targetURL')
    scanId = str(random.randint(1000000,9999999))
    nowtime = int(time.time())
    EIToken = request.cookies.get('EIToken')
    info_token = EIToken.split('.')[1]
    userId,userName = getUserIdFromToken(EIToken)

    timeStamp = request.args.get('timeStamp')
    period = request.args.get('period')

    #Passive scan setting
    precurse = request.args.get('precurse')
    subtreeOnly= request.args.get('subtreeOnly') 
    maxChildren=''
    contextName=''

    #Active scan setting
    arecurse = request.args.get('arecurse')
    inScopeOnly = request.args.get('inScopeOnly')
    method = ''
    postData = ''
    contextId = ''
    alertThreshold = request.args.get('alertThreshold')
    attackStrength = request.args.get('attackStrength')

    nowScan = db.listScanning()
    if timeStamp != '0':
        print(timeStamp)
        print(type(timeStamp))
        #Call Dashboard API getting dashboardLink
        try:
            dashboardLink = create_dashboard(appURL,apiURL,scanId,EIToken)
        except Exception:
            abort(400)
        #Add html to db
        html_info = {
            "userId":userId,
            "scanId":scanId,
            "html":""
        }
        db.addHtml(html_info)
        
        if scanOption == '0':
            scandata = {
                "userId":userId,
                "userName":userName,
                "scanId":scanId,
                "targetURL":targetURL,
                "dashboardLInk":dashboardLink,
                "timeStamp":int(timeStamp),
                "ascanStatus":'0',
                "pscanStatus":'0',
                "scanOption":scanOption,
                "ascanId":'-1',
                "pscanId":'-1',
                "status":'0',
                "schedule":'1',
                "period":int(period),
                "pscanInfo":{
                    "recurse": precurse,
                    "subtreeOnly": subtreeOnly,
                    "maxChildren":'',
                    "contextName":''
                },
                "ascanInfo":{
                    "recurse" : '',
                    "inScopeOnly" : '',
                    "method" : '',
                    "postData" : '',
                    "contextId" : '',
                    "alertThreshold" : '',
                    "attackStrength" : ''
                }
            }

        elif scanOption == '2':

            scandata = {
                "userId":userId,
                "userName":userName,
                "scanId":scanId,
                "targetURL":targetURL,
                "dashboardLInk":dashboardLink,
                "timeStamp":int(timeStamp),
                "ascanStatus":'0',
                "pscanStatus":'0',
                "scanOption":scanOption,
                "ascanId":'-1',
                "pscanId":'-1',
                "status":'0',
                "schedule":"1",
                "period":int(period),
                "pscanInfo":{
                    "recurse": precurse,
                    "subtreeOnly": subtreeOnly,
                    "maxChildren":'',
                    "contextName":''
                },
                "ascanInfo":{
                    "recurse" : arecurse,
                    "inScopeOnly" : inScopeOnly,
                    "method" : '',
                    "postData" : '',
                    "contextId" : '',
                    "alertThreshold" : alertThreshold,
                    "attackStrength" : attackStrength
                }
            }

        db.addScan(scandata)
        
        result = jsonify({"Result":"SCHEDULE"})
        result.set_cookie('scanId',scanId,domain=domainName)
        return result
        

    elif nowScan != None:

             
        #Call Dashboard API getting dashboardLink
        try:
            dashboardLink = create_dashboard(appURL,apiURL,scanId,EIToken)
        except Exception as err:
            abort(400)
        
        #Add html to db
        html_info = {
            "userId":userId,
            "scanId":scanId,
            "html":""
        }
        db.addHtml(html_info)
    
        # timeStamp => int type
        # other info  => str type
        
        
        if scanOption == '0':
            scandata = {
                "userId":userId,
                "userName":userName,
                "scanId":scanId,
                "targetURL":targetURL,
                "dashboardLInk":dashboardLink,
                "timeStamp":nowtime,
                "ascanStatus":'0',
                "pscanStatus":'0',
                "scanOption":scanOption,
                "ascanId":'-1',
                "pscanId":'-1',
                "status":'0',
                "schedule":'1',
                "period":int(period),
                "pscanInfo":{
                    "recurse": precurse,
                    "subtreeOnly": subtreeOnly,
                    "maxChildren":'',
                    "contextName":''
                },
                "ascanInfo":{
                    "recurse" : '',
                    "inScopeOnly" : '',
                    "method" : '',
                    "postData" : '',
                    "contextId" : '',
                    "alertThreshold" : '',
                    "attackStrength" : ''
                }
            }

        elif scanOption == '2':

            scandata = {
                "userId":userId,
                "userName":userName,
                "scanId":scanId,
                "targetURL":targetURL,
                "dashboardLInk":dashboardLink,
                "timeStamp":nowtime,
                "ascanStatus":'0',
                "pscanStatus":'0',
                "scanOption":scanOption,
                "ascanId":'-1',
                "pscanId":'-1',
                "status":'0',
                "schedule":"1",
                "period":int(period),
                "pscanInfo":{
                    "recurse": precurse,
                    "subtreeOnly": subtreeOnly,
                    "maxChildren":'',
                    "contextName":''
                },
                "ascanInfo":{
                    "recurse" : arecurse,
                    "inScopeOnly" : inScopeOnly,
                    "method" : '',
                    "postData" : '',
                    "contextId" : '',
                    "alertThreshold" : alertThreshold,
                    "attackStrength" : attackStrength
                }
            }

        db.addScan(scandata)

        result = jsonify({"Result":"NEEDWAITING"})
        result.set_cookie('scanId',scanId,domain=domainName)
        return result
    else:
        
        # Delete all previous datas on ZAP server
        r_delete = requests.get('http://127.0.0.1:5000/JSON/core/action/deleteAllAlerts')
        if r_delete.status_code == 200:
            
            # Get params from user setting
            #scanOption = request.args.get('scanOption')
            #targetURL = request.args.get('targetURL')
            #precurse = request.args.get('precurse')
            #subtreeOnly= request.args.get('subtreeOnly') 
            #maxChildren=''
            #contextName=''

            payload = {'url': targetURL, 'maxChildren': maxChildren,'recurse':precurse,'contextName':contextName ,'subtreeOnly':subtreeOnly}
            r_passive = requests.get('http://127.0.0.1:5000/JSON/spider/action/scan',params=payload)
            if r_passive.status_code == 200:
                r_passive = r_passive.json() 
                pscanId = r_passive['scan']
                #scanId = str(random.randint(1000000,9999999))
                #nowtime = int(time.time())
                #EIToken = request.cookies.get('EIToken')
                #info_token = EIToken.split('.')[1]
                #userId = getUserIdFromToken(EIToken)

                
                #call Dashboard API getting dashboardLink
                try:
                    dashboardLink = create_dashboard(appURL,apiURL,scanId,EIToken)
                except Exception as err:
                    abort(400)
    
                # timeStamp => int type
                # other info  => str type
                scandata = {
                    "userId":userId,
                    "userName":userName,
                    "scanId":scanId,
                    "targetURL":targetURL,
                    "dashboardLInk":dashboardLink,
                    "timeStamp":nowtime,
                    "ascanStatus":'0',
                    "pscanStatus":'0',
                    "scanOption":scanOption,
                    "ascanId":'-1',
                    "pscanId":pscanId,
                    "status":'1',
                    "schedule":'0',
                    "period":0
                }
                db.addScan(scandata)
    
                html_info = {
                    "userId":userId,
                    "scanId":scanId,
                    "html":""
                }
                db.addHtml(html_info)
                
                #thread
                if scanOption == '0':
                    global checkPassiveStatusThread
                    checkPassiveStatusThread = threading.Thread(target=checkPassiveStatus,args=[scanId])
                    checkPassiveStatusThread.start()
                elif scanOption == '2':
                    global checkActiveStatusThread
                    #arecurse = request.args.get('arecurse')
                    #inScopeOnly = request.args.get('inScopeOnly')
                    #method = ''
                    #postData = ''
                    #contextId = ''
                    #alertThreshold = request.args.get('alertThreshold')
                    #attackStrength = request.args.get('attackStrength')
                    checkActiveStatusThread = threading.Thread(target=checkActiveStatus,args=[scanId,targetURL,arecurse,inScopeOnly,method,postData,contextId,alertThreshold,attackStrength])
                    checkActiveStatusThread.start()

                
                
                #set scanId to cookie
                result = jsonify({"Result":"SCANNING"})
                result.set_cookie('scanId',scanId,domain=domainName)
                return result
            else:
                print('passive scan start error!')


        else:
            print('passive scan delete error!')
  
# cancel button
@app.route('/cancelStartScan',methods=['GET'])
@EIToken_verification
def cancelStartScan():
    try:
        scanId = request.cookies.get('scanId')
        rp = requests.get('http://127.0.0.1:5000/JSON/spider/action/removeAllScans/')   
        ra = requests.get('http://127.0.0.1:5000/JSON/ascan/action/removeAllScans/')    
        rp = rp.json()
        ra = ra.json()
        if rp['Result'] == 'OK' and ra['Result']=='OK':
        
            r_html = requests.get('http://127.0.0.1:5000/OTHER/core/other/htmlreport/')
            if r_html.status_code == 200:
                db.modifyExistHtml('html',r_html.content,scanId)
                db.modifyExistInfo('status','3',scanId)
                result = {'Result':'OK'}
                return jsonify(result)
            else:
                abort(500)
        else:
            abort(500)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/cancelNotStartScan',methods=['GET'])
@EIToken_verification
def cancelNotStartScan():
    scanId = request.cookies.get('scanId')
    db.deleteScan(scanId)
    return jsonify({'Result':'OK'})

@app.route('/pscanStatusDB',methods=['GET'])
@EIToken_verification
def pscanStatusDB():
    try:
        scanId = request.cookies.get('scanId')
        if scanId:
            scan_info = db.findScan(scanId)
            pscanStatus = scan_info['pscanStatus']
            result = {'status':pscanStatus}
            return jsonify(result)
        else:
            result = {'status':'-1'}
            return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/fullScanStatusDB',methods=['GET'])
@EIToken_verification
def fullScanStatusDB():
    try:
        scanId = request.cookies.get('scanId')
        if scanId:
            scan_info = db.findScan(scanId)
            ascanStatus = scan_info['ascanStatus']
            pscanStatus = scan_info['pscanStatus']
            if int(pscanStatus) <= 100 and int(ascanStatus) ==0:
                result = {'scanType':'Passive scan','status':pscanStatus}                
                return jsonify(result)
            elif int(pscanStatus) == 100 and int(ascanStatus)<=100:
                result = {'scanType':'Active scan','status':ascanStatus}                
                return jsonify(result)
                
        else:
            result = {'status':'-1'}
            return result
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/addScan',methods=['GET'])
@EIToken_verification
def addScan():
    targetURL = request.args.get('targetURL')
    scanOption = request.args.get('scanOption')
    spiderId =request.cookies.get('spiderId')  
    scanId = str(random.randint(1000000,9999999))
    nowtime = int(time.time())
    EIToken = request.cookies.get('EIToken')
    info_token = EIToken.split('.')[1]
    userId = getUserIdFromToken(EIToken)
        
    #call Dashboard API getting dashboardLink
    #dashboardLink = 'https://portal-sso.arfa.wise-paas.com'
    dashboardLink = create_dashboard(appURL,apiURL,scanId,EIToken)
    # timeStamp => int
    # other info  => str
    scandata = {
        "userId":userId,
        "scanId":scanId,
        "targetURL":targetURL,
        "dashboardLInk":dashboardLink,
        "timeStamp":nowtime,
        "ascanStatus":'0',
        "pscanStatus":'0',
        "scanOption":scanOption,
        "ascanId":'-1',
        "spiderId":spiderId,
        "status":'0'
    }
    db.addScan(scandata)
    
    html_info = {
        "userId":userId,
        "scanId":scanId,
        "html":""
    }
    db.addHtml(html_info)
    res_cookie = make_response(redirect('/'),200)
    res_cookie.set_cookie('scanId',scanId,domain=domainName)
    return res_cookie

@app.route('/refreshTable',methods=['GET'])
@EIToken_verification
def refreshTable():
    timeZone = request.args.get('timeZone')
    EIToken =request.cookies.get('EIToken')
    info_token = EIToken.split('.')[1]
    userId,userName = getUserIdFromToken(EIToken)
    scans = db.listUserScans(userId)
    #print(userId)
    #print(scans)
    for scan in scans:
        ts = scan['timeStamp'] 
        ts+=int(timeZone)*60*60
        time = datetime.fromtimestamp(ts).strftime('%Y/%m/%d %H:%M')
        time_info = {'time' : time}
        scan.update(time_info)
    return jsonify(scans)

@app.route('/refreshScheduleTable',methods=['GET'])
@EIToken_verification
def refreshScheduleTable():
    timeZone = request.args.get('timeZone')
    EIToken =request.cookies.get('EIToken')
    info_token = EIToken.split('.')[1]
    userId,userName = getUserIdFromToken(EIToken)
    scans = db.listUserPendingScans(userId)
    for scan in scans:
        ts = scan['timeStamp']
        ts+=int(timeZone)*60*60
        time = datetime.fromtimestamp(ts).strftime('%Y/%m/%d %H:%M')
        time_info = {'time' : time}

        per = scan['period']
        day = 86400
        if per ==  0:
            period_info = {'period': 'Only Once'}
        else:
            period_info = {'period': str(int(per/day)) + ' day'}
        scan.update(time_info)
        scan.update(period_info)
    return jsonify(scans)
'''
@app.route('/setSSOurl')
def setSSOurl():
    res_cookie = make_response(redirect('/'),200)
    res_cookie.set_cookie('SSO_URL', ssoUrl,domain=domainName)
    return res_cookie
'''

@app.route('/checkDashboardUrl')
@EIToken_verification
def checkDashboardUrl():
    EIToken = request.cookies.get('EIToken')
    global apiURL
    global appURL
    url = db.getDashboardUrl()
    if url == None:
        return jsonify({'Result':'None'})
    else:
        apiURL = url
        create_datasource.create_datasource(apiURL, appURL, "ZAP-Summary","/summary/", EIToken)       
        create_datasource.create_datasource(apiURL, appURL, "ZAP-Progress","/progress/", EIToken)
        return jsonify({'Result':'OK'})

@app.route('/updateDashboardUrl')
@EIToken_verification
def updateDashboardUrl():
    EIToken = request.cookies.get('EIToken')
    url = request.args.get('dashboardUrl')
    global apiURL
    global appURL
    apiURL = url
    create_datasource.create_datasource(apiURL, appURL, "ZAP-Summary","/summary/", EIToken)       
    create_datasource.create_datasource(apiURL, appURL, "ZAP-Progress","/progress/", EIToken)

    db.updateDashbardUrl(url)
    return jsonify({'Result':'OK'})

@app.route('/emailServiceInfo')
@EIToken_verification
def emailServiceInfo():
    EIToken = request.cookies.get('EIToken')
    userId,userName = getUserIdFromToken(EIToken)
    info = db.checkEmailService(userId)
    if  info != None :
        return jsonify(info)
    else:
        return 'None'
     
@app.route('/emailServiceSetting')
@EIToken_verification
def emailServiceSetting():
    EIToken = request.cookies.get('EIToken')
    userId,userName = getUserIdFromToken(EIToken)
    notificationURL = request.args.get('notificationURL')
    SMTPServerURL = request.args.get('SMTPServerURL')
    serverPort= request.args.get('serverPort')
    SMTPUsername = request.args.get('SMTPUsername')
    SMTPPassword = request.args.get('SMTPPassword')
    SMTPSender = request.args.get('SMTPSender')
    secure = request.args.get('secure')
    secureMethod = request.args.get('secureMethod')
    SSOAccount = request.args.get('SSOAccount')
    SSOPassword = request.args.get('SSOPassword')
    
    if secure == 'true':
        secure = True
    else: 
        secure = False
    try:
        groupId = create_group(notificationURL,"Web_App_Scanner",SMTPServerURL,serverPort,
                SMTPUsername,SMTPPassword,SMTPSender,secure,secureMethod,EIToken)
    except:
        return jsonify({'Result':'notification configured error'})
    data = {
       "userId":userId,  
       "notificationURL":notificationURL,
       "SMTPServerURL":SMTPServerURL,
       "serverPort":int(serverPort),
       "SMTPUsername":SMTPUsername,
       "SMTPPassword":SMTPPassword,
       "SMTPSender":SMTPSender,
       "secure":secure,
       "secureMethod":secureMethod,
       "SSOAccount":SSOAccount,
       "SSOPassword":SSOPassword,
       "groupId":groupId
    }
    
    if db.checkEmailService(userId) != None :
        print('exist')
        db.updateEmailService(userId,data)
    else:
        print('add')
        db.addEmailService(data)
    return jsonify({'Result':'OK'})
'''
SPIDER + PASSIVE SCAN
'''
@app.route('/spiderScan')
@EIToken_verification
def spiderScan():
    url = request.args.get('url')
    maxChildren=''
    recurse = request.args.get('recurse')
    contextName=''
    subtreeOnly= request.args.get('subtreeOnly')
    try:
        payload = {'url': url, 'maxChildren': maxChildren,'recurse':recurse,'contextName':contextName ,'subtreeOnly':subtreeOnly}
        r = requests.get('http://127.0.0.1:5000/JSON/spider/action/scan',params=payload)
        if r.status_code == 200:
            r = r.json()
            res_cookie = make_response(redirect('/'),200)
            res_cookie.set_cookie('spiderId', r['scan'],domain=domainName)
            res_cookie.set_cookie('targetUrl', url,domain=domainName)
        
            return res_cookie
        else:
            abort(500)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)
        
@app.route('/pscanStatus')
@EIToken_verification
def pscanStatus():
    try:
        scanId = request.cookies.get('scanId')
        scan_info = db.findScan(scanId)
        pscanId = scan_info['pscanId']
        payload = {'scanId':pscanId}
        r = requests.get('http://127.0.0.1:5000/JSON/spider/view/status/',params=payload)   
        r = r.json()
        status = r['status']
        db.modifyExistInfo('pscanStatus',status,scanId)
        
        r_html = requests.get('http://127.0.0.1:5000/OTHER/core/other/htmlreport/')
        if r_html.status_code == 200:
            db.modifyExistHtml('html',r_html.content,scanId)

        result = {'status':status}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/spiderPause')
@EIToken_verification
def spiderPause():
    try:
        spiderId=request.cookies.get('spiderId')
        payload = {'scanId':spiderId}
        r = requests.get('http://127.0.0.1:5000/JSON/spider/action/pause/',params=payload)  
        r = r.json()
        result = {'Result':r['Result']}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/spiderResume')
@EIToken_verification
def spiderResume():
    try:
        spiderId=request.cookies.get('spiderId')
        payload = {'scanId':spiderId}
        r = requests.get('http://127.0.0.1:5000/JSON/spider/action/resume/',params=payload) 
        r = r.json()
        result = {'Result':r['Result']}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/spiderRemove')
@EIToken_verification
def spiderRemove():
    try:
        r = requests.get('http://127.0.0.1:5000/JSON/spider/action/removeAllScans/')    
        r = r.json()
        result = {'Result':r['Result']}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)
'''
ACTIVE SCAN
'''
@app.route('/ascan')
@EIToken_verification
def ascan():
    url = request.cookies.get('targetUrl')
    scanId = request.cookies.get('scanId')
    recurse = request.args.get('recurse')
    inScopeOnly = request.args.get('inScopeOnly')
    scanPolicyName = 'custom'
    method =''
    postData = ''
    contextId = ''
    try:
        payload = {'url' : url,'inScopeOnly':inScopeOnly,'recurse':recurse,'scanPolicyName':scanPolicyName,'method':method,'postData':postData,'contextId':contextId}
        r = requests.get('http://127.0.0.1:5000/JSON/ascan/action/scan/',params=payload)
        if r.status_code == 200:
            r = r.json()
            res_cookie = make_response(redirect('/'),200)
            res_cookie.set_cookie('ascanId', r['scan'],domain=domainName)
            db.modifyExistInfo('ascanId',r['scan'],scanId)
            db.modifyExistInfo('status','2',scanId)
            return res_cookie
        else:
            abort(500)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/addScanPolicy')
@EIToken_verification
def addScanPolicy():
    try:
        scanPolicyName = 'custom'
        remove_payload = {'scanPolicyName':scanPolicyName}
        r_remove = requests.get('http://127.0.0.1:5000/JSON/ascan/action/removeScanPolicy/',params=remove_payload)
        if r_remove.status_code == 200 or r_remove.status_code == 400:
            alertThreshold = request.args.get('alertThreshold')
            attackStrength = request.args.get('attackStrength')
            payload = {'scanPolicyName':scanPolicyName,'alertThreshold':alertThreshold,'attackStrength':attackStrength}
            r = requests.get('http://127.0.0.1:5000/JSON/ascan/action/addScanPolicy',params=payload)
            result = {'code':r.status_code}
            return jsonify(result)
        else:
            abort(400)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/ascanStatus')
@EIToken_verification
def ascanStatus():
    try:
        scanId = request.cookies.get('scanId')
        scan_info = db.findScan(scanId)
        ascanId = scan_info['ascanId']
        #ascanId=request.cookies.get('ascanId')
        payload = {'ascanId':ascanId}
        r = requests.get('http://127.0.0.1:5000/JSON/ascan/view/status/',params=payload)    
        r = r.json()
        status = r['status']
        db.modifyExistInfo('ascanStatus',status,scanId)
        
        r_html = requests.get('http://127.0.0.1:5000/OTHER/core/other/htmlreport/')
        if r_html.status_code == 200:
            db.modifyExistHtml('html',r_html.content,scanId)
        
        result = {'status':r['status']}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/ascanPause')
@EIToken_verification
def ascanPause():
    try:
        ascanId=request.cookies.get('ascanId')
        payload = {'scanId':ascanId}
        r = requests.get('http://127.0.0.1:5000/JSON/ascan/action/pause/',params=payload)   
        r = r.json()
        result = {'Result':r['Result']}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/ascanResume')
@EIToken_verification
def ascanResume():
    try:
        ascanId=request.cookies.get('ascanId')
        payload = {'scanId':ascanId}
        r = requests.get('http://127.0.0.1:5000/JSON/ascan/action/resume/',params=payload)  
        r = r.json()
        result = {'Result':r['Result']}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/ascanRemove')
@EIToken_verification
def ascanRemove():
    try:
        r = requests.get('http://127.0.0.1:5000/JSON/ascan/action/removeAllScans/') 
        r = r.json()
        result = {'Result':r['Result']}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/clear')
@EIToken_verification
def clear():
    try:
        r = requests.get('http://127.0.0.1:5000/JSON/core/action/deleteAllAlerts')
        r = r.json()
        result = {'Result':r['Result']}
        return jsonify(result)
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

## Web check scan

@app.route('/checkScan',methods=['GET'])
@cross_origin()
def checkScan():
    try:
        scanId =request.cookies.get('scanId') 
        scan = db.findScan(scanId)
        scanOption = scan['scanOption']
        spiderId = scan['spiderId']
        status = scan['status']
        if status == 3:
            result = {'Result':'OK'}
            return jsonify(result)      
        else:
            result = {'Result':'SCAN'}
            return jsonify(result)      
    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

'''
checkAnyScan is for checking if there is any scan on ZAP api server
it prevents zap api server from multi-scanning.(Now only support scanning once for one browser page) 
when starting a new scan,browser will stop timer of calling checkAnyScan.
If scan has finished or been stopped,timer would resume to check it.
'''
@app.route('/checkAnyScan',methods=['GET'])
@EIToken_verification
def checkAnyScan():
    try:
        scans = db.listNotFinishedScans()
        if len(scans) !=0:
            result = {'Result':'NO'}
        elif len(scans) == 0:
            result = {'Result':'OK'}
        return jsonify(result)

    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)

@app.route('/checkUserScan',methods=['GET'])
@EIToken_verification
def checkUserScan():
    try:
    
        EIToken = request.cookies.get('EIToken')
        info_token = EIToken.split('.')[1]
        userId,userName = getUserIdFromToken(EIToken)
        scan = db.listUserNotFinishedScan(userId)
        if scan == None:
            result = {'Result':'NOSCAN'}
            return jsonify(result)
        elif scan['status'] == '1' or scan['status'] == '2':
            scanId = scan['scanId']
            scanOption = scan['scanOption']
            result = jsonify({'Result':'SCANNING','scanOption':scanOption})
            result.set_cookie('scanId',scanId,domain=domainName)
            return result
        elif scan['status'] == '0':
            scanId = scan['scanId']
            scanOption = scan['scanOption']
            result = jsonify({'Result':'NEEDWAITING','scanOption':scanOption})
            result.set_cookie('scanId',scanId,domain=domainName)
            return result
            


    except Exception as err:
        print('error: {}'.format(str(err)))
        abort(500)
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080,debug=False)
