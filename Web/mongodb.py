#-*-coding:utf-8 -*- 
import pymongo
import json
import os
import random
import time
from datetime import datetime



class mongoDB():
    def __init__(self):
        try:
            app_env = json.loads(os.environ['VCAP_SERVICES'])
            self.mongoUri = app_env['mongodb'][0]['credentials']['uri']
            self.dbname = app_env['mongodb'][0]['credentials']['database']
            print('get db environment variables!')
        except Exception as err:
            print('Can not get db environment variables:{}'.format(str(err)))
        self.client = pymongo.MongoClient(self.mongoUri)
        self.db = self.client[self.dbname]
        self.collection = self.db.scans
        self.coll_html = self.db.htmls
        self.coll_initInfo = self.db.initInfo
        self.coll_emailService = self.db.emailService
        print("connect to mongoDB!")    
    
    #emailService
    def updateEmailService(self,userId,data):
        self.coll_emailService.update({'userId':userId},data)
    
    def checkEmailService(self,userId):
        result = self.coll_emailService.find_one({'userId':userId},{"_id":0})
        return result
    def addEmailService(self,data):
        self.coll_emailService.insert_one(data)
    def findAllEmailService(self):
        results = self.coll_emailService.find({},{"_id":0})
        info = []
        for result in results:
            info.append(result)
        return info
    def deleteAllEmailService(self):
        result = self.coll_emailService.remove({})

    #init info
    def updateDashbardUrl(self,url):
        self.coll_initInfo.update({'num':'1'},{'$set':{'dashboardUrl':url}},True)
    def setDashbardUrl(self,url):
        data = {
            'num':1,
            'dashboardUrl':url
        }
        self.coll_initInfo.insert_one(data)
    def getDashboardUrl(self):
        result = self.coll_initInfo.find_one({"num":'1'})
        if result:
            return result['dashboardUrl']
        else:
            return None;
    def getAllDashboardUrl(self):
        results = self.coll_initInfo.find({},{"_id":0})
        scans = []
        for result in results:
            scans.append(result)
        return scans
    def showInitInfo(self):
        result = self.coll_initInfo.find({'num':'1'})
        print(result)

    def getCollection(self):
        coll_name = self.db.collection_names(session=None)
        return coll_name
    def addScan(self,data):
        result = self.collection.insert_one(data)
    def addHtml(self,data):
        result = self.coll_html.insert_one(data)
    def findScan(self,scanId):
        result = self.collection.find_one({"scanId":scanId})
        return result
    def modifyExistInfo(self,key,value,scanId):
        self.collection.update({'scanId':scanId},{'$set':{key:value}})
    def modifyExistHtml(self,key,value,scanId):
        self.coll_html.update({'scanId':scanId},{'$set':{key:value}})
    def findHtml(self,scanId):
        result = self.coll_html.find_one({"scanId":scanId})
        return result
    def listUserScans(self,userId):
        results = self.collection.find({
            "$and":[
                {'userId':userId},
                {'status':{ '$ne':'0' }},
                {'status':{ '$ne':'4' }}
 
            ]},{"_id":0}).sort('timeStamp',pymongo.DESCENDING)
        scans = []
        for result in results:
            scans.append(result)
        return scans
    def listUserPendingScans(self,userId):
        results = self.collection.find({
            "$and":[
                {'userId':userId},
                {'status':'0'}
            ]},{"_id":0}).sort('timeStamp',pymongo.ASCENDING)
        scans = []
        for result in results:
            scans.append(result)
        return scans
    def listFinishedScans(self,userId):
        results = self.collection.find({
            "$and":[
                {'userId':userId},
                {'status':'3'}
 
            ]},{"_id":0}).sort('timeStamp',pymongo.DESCENDING)
        scans = []
        for result in results:
            scans.append(result)
        return scans
    def listAllScans(self):
        results = self.collection.find({},{"_id":0}).sort('timeStamp',pymongo.ASCENDING)
        scans = []
        for result in results:
            scans.append(result)
        return scans
    def listNotFinishedScans(self):
        results = self.collection.find({
            "$and":[
                {'userId':userId},
                {'status':{ '$ne':'3' }},
                {'status':{ '$ne':'4' }}
            ]},{"_id":0}).sort(('timeStamp',pymongo.DESCENDING))
        scans = []
        for result in results:
            scans.append(result)
        return scans
    def readyScans(self):
        results = self.collection.find({'status':'0'},{"_id":0}).sort('timeStamp',pymongo.ASCENDING)
        scans = []
        for result in results:
            scans.append(result)
        return scans
    def listUserNotFinishedScan(self,userId):
        scan = self.collection.find_one({
            "$and":[
                {'userId':userId},
                {'status':{ '$ne':'3' }},
                {'status':{ '$ne':'4' }}
            ]},{"_id":0})
        return scan
    def listScanning(self):
        # Not (0 or 3) => (not 0) and (not 3)
        scan = self.collection.find_one({
            "$and":[
                    {"status":{"$ne":"0"}},
                    {"status":{"$ne":"3"}},
                    {"status":{"$ne":"4"}}
                    
            ]},{"_id":0})
        return scan
    def deleteScan(self,scanId):
        result = self.collection.remove({'scanId': scanId})
        result_html = self.coll_html.remove({'scanId':scanId})
    def deleteDashboardUrl(self):
        result = self.coll_initInfo.remove({'num':'1'})
    def deleteScans(self,scanIdlist):
        for scanId in scanIdlist:
            result = self.collection.remove({'scanId': scanId})
            result_html = self.coll_html.remove({'scanId':scanId})
    def deleteRunningScans(self):
        result = self.collection.remove({
            "$and":[
                {'status':{ '$ne':'0' }},
                {'status':{ '$ne':'3' }},
                {'status':{ '$ne':'4' }}
            ]},{"_id":0})

    def deleteAllScans(self):
        result = self.collection.remove({})

if __name__ == '__main__':
    mongodb = mongoDB()

    userId = 'hello'
    scanId = str(random.randint(1000000,9999999))
    targetURL = 'http://testphp.vulnweb.com'
    dashboardLink  = 'http://www.google.com'
    nowtime = int(time.time())
    scanOption = '0'
    precurse = 'true'
    subtreeOnly = 'false'

    html_info = {
             "userId":userId,
             "scanId":scanId,
             "html":""
         }
    mongodb.addHtml(html_info)





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
                "pscanId":'-1',
                "status":'0',
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


    
    
    #scans = mongodb.listScans('b7ea79a3-c2eb-4c79-b968-b279667f3747')
    #print(scans)
    #print(len(scans))
    #scan = mongodb.findScan('6574903') 
    #print(scan)
    '''
    for scan in scans:
        ts = scan['timeStamp']
        time = datetime.fromtimestamp(ts).strftime('%Y/%m/%d %H:%M')
        time_info = {'time' : time}
        scan.update(time_info)
    '''
    #print(time_info)


    #print(scans)
    #mongodb.deleteAllScans()
    #mongodb.addScan(scandata)
    #mongodb.deleteScans(['8829705','2962665'])
    #scans = mongodb.listAllScans()
    #print(scans)
    #scans = mongodb.listUserScans('b7ea79a3-c2eb-4c79-b968-b279667f3747')
    #print(len(scans))
    '''
    for scan in scans:
        print("status: " + scan['status']+" \npscan: "+ scan['pscanStatus']+" \nascan: "+ scan['ascanStatus']+" \ntimeStamp: "+ str(scan['timeStamp'])+" \nuserId: "+ str(scan['userId']))
    '''
    #scans = mongodb.getAllDashboardUrl()
    #print(scans)
    #mongodb.deleteDashboardUrl()
    #print(mongodb.getCollection())
    #html = mongodb.findHtml('666')
    #print(html)
    #scanId =str(777)
    #mongodb.modifyExistInfo('ascanId','0',scanId)

    #scan = mongodb.findScan(scanId)    
    #print(scan)

    #scans = mongodb.listNotFinishedScans()
    #print(scans)
    
    #scan = mongodb.listScanning()
    #print(scan)

    #scans = mongodb.readyScans()
    #print(scans)
    #print(len(scans))


    mongodb.deleteAllEmailService()
    #print(info)
