import sys
import requests
import json
import random
from flask import Flask,request,redirect
from flask import jsonify,abort,Response, make_response

#appURL = 'https://zap-security-web-v4.arfa.wise-paas.com' #Should be got from env
#EItoken = '' #Should be got from user's browser

def create_datasource(dashboardURL, appURL, name, route, token):
  my_headers = {'Content-Type':'application/json',
                'Authorization': 'Bearer {}'.format(token)}
  payload ={
    "name":name,
    "type":"grafana-simple-json-datasource",
    "url":appURL + route,
    "access":"proxy"
  } 
  res = requests.post(dashboardURL + "/api/datasources", headers=my_headers, json=payload)
  try:
      print( "Your datasource is " +appURL+"/"+res.json()["name"] )
  except:
      print("Updating Your Datasource")
      res = requests.delete(dashboardURL + "/api/datasources/name/" + name, headers=my_headers, json=payload)
      print("Old Datasource Deleted")
      res = requests.post(dashboardURL + "/api/datasources", headers=my_headers, json=payload)
      print("New Datasource Updated")
      print(res.text)
      
