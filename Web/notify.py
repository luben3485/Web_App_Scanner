import sys
import requests
import json
import base64
from flask import Flask,request,redirect
from flask import jsonify,abort,Response, make_response
import mongodb
from rsa_decrypt import decrypt_password
from report import process_report

def create_group(notificationURL,name,server,port,user,password,sender,secure,method,token): 
    my_headers = {'Content-Type':'application/json',
    'Authorization': 'Bearer {}'.format(token)}
    payload = {
        "name": name,
        "description": "EnSaaS Web App Scanner Notify Service",
        "type": "email",
        "levelName": "Critical",
        "config": {
          "host": server,
          "port": port,
          "secure": secure,
          "method": method,
          "username": user,
          "password": password,
          "senderEmail": sender,
          "emailSubject": "Web App Scanner Notice",
          "template": """<p><img src="data:image/png;base64,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" style="width:45%" /></p>

        <hr />
        <p><span style="font-size:16px"><span style="font-family:Arial,Helvetica,sans-serif">Hi {name},&nbsp;</span></span></p>

        <p style="margin-left:40px"><span style="font-size:16px"><span style="font-family:Arial,Helvetica,sans-serif">Thank you for using our Web App Scanner service.</span></span></p>

        <p style="margin-left:40px"><span style="font-size:16px"><span style="font-family:Arial,Helvetica,sans-serif">Your Security Scan with ID {scan_id}&nbsp; is completed.</span></span></p>

        <p style="margin-left:40px"><span style="font-size:16px"><span style="font-family:Arial,Helvetica,sans-serif">The Summary Report is attached for your reference. Have a good day!</span></span></p>

        <p><span style="font-size:16px"><span style="font-family:Arial,Helvetica,sans-serif">Best,</span><br />
        <span style="font-family:Arial,Helvetica,sans-serif"><strong><span style="color:#003366">WISE-PaaS/</span><span style="color:#2980b9">Web App Scanner</span></strong> Team</span></span></p>

        <hr />
        <p><strong><span style="font-size:14px"><span style="font-family:Arial,Helvetica,sans-serif">Automatically sent with <span style="color:#003366">WISE-PaaS/</span><span style="color:#2980b9">Notification</span>.&nbsp;</span></span></strong><strong><span style="font-size:14px"><span style="font-family:Arial,Helvetica,sans-serif">Please do not reply.</span></span></strong></p>
            """
        },
        "sendList": [
            {
            "firstName": "Firstname",
            "lastName": "Lastname",
            "recipientType": "to",
            "target": "test@advantech.com.tw"
            }
        ]
      }
    res = requests.post(notificationURL + "/api/v1.5/Groups", 
        headers=my_headers, json=payload)
    try:
        return res.json()["groupId"]
    except:
        res = requests.get(notificationURL + "/api/v1.5/Groups/" + name,
            headers=my_headers)
        print("Delete and Create:" + res.text)
        oldId = res.json()["groupId"]
        delete_group(notificationURL,oldId,token)
        res = requests.post(notificationURL + "/api/v1.5/Groups",
            headers=my_headers, json=payload)
        return res.json()["groupId"]

def delete_group(notificationURL,groupId,token):
    my_headers = {'Content-Type':'application/json',
        'Authorization': 'Bearer {}'.format(token)}
    payload = [
        groupId
      ]
    res = requests.delete(notificationURL + "/api/v1.5/Groups",
        headers=my_headers, json=payload)
    print("Delete:" + res.text)

def send_email(notificationURL,groupId, email, name, scanID, file_string,token):
    my_headers = {'Content-Type':'application/json',
    'Authorization': 'Bearer {}'.format(token)}
    payload = {
          "groupId": groupId,
          "useTemplate": True,
          "message": "string",
          "variables": {"name":name,"scan_id":scanID},
          "sendList": [
            {
              "target": email,
              "recipientType": "to"
            }
          ],
          "attachments": [
            {
              "filename": "Summary_Report.html",
              "content": file_string
            }
          ]
        } 
    res = requests.post(notificationURL + "/api/v1.5/Groups/send",
        headers=my_headers, json=payload)
    if (res.json()[0]["result"][0]["isSuccess"]): print("The email is sent!")

def encode(html):
    b64_bytes = base64.b64encode(html)
    b64_string = b64_bytes.decode('ascii')
    return b64_string

def get_token(ssoURL,userID):
    db = mongodb.mongoDB()
    user = db.checkEmailService(userID)
    try:
      username = user["SSOAccount"]
      password = decrypt_password( user["SSOPassword"] )
      my_headers = {'Content-Type':'application/json'}
      payload = {
        "username": username,
        "password": password
      }
      res = requests.post(ssoURL+"/v2.0/auth",headers=my_headers,json=payload)
      return res.cookies['EIToken']
    except:
      print("authentication failed or user not found in DB.")
      print(password)

def send_mail_by_scanID(ssoURL,scanID):
    try:
      db = mongodb.mongoDB()
      userID = db.findScan(scanID)["userId"]
      user = db.checkEmailService(userID)
      EItoken = get_token(ssoURL,userID)
      notificationURL = user["notificationURL"]
      groupId = user["groupId"]
      info = EItoken.split('.')[1]
      lenx = len(info)%4
      if lenx == 1:
          info += '==='
      if lenx == 2:
          info += '=='
      if lenx == 3:
          info += '='
      email = json.loads(base64.b64decode(info))['username']
      name = db.findScan(scanID)["userName"]
      file_string = encode( process_report(db.findHtml(scanID)["html"]) )
      token = EItoken
      send_email(notificationURL,groupId,email,name,scanID,file_string,token)
    except Exception as err:
      print( "fail to send email, because {}".format(err) )
#file_string is a b64 string encoded from a file