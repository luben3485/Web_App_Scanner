import re
from flask import Flask,request
from flask import jsonify,abort,Response, make_response
from flask_cors import cross_origin

High = {}
Medium = {}
Low = {}
Informational = {}
Passive_Scan_Progress = {}
Active_Scan_Progress = {} 

import os
app = Flask(__name__,static_url_path='',root_path=os.getcwd())
import mongodb
db = mongodb.mongoDB()

@app.route('/summary/')
def health_check():
    return "This datasource is healthy"

@app.route('/progress/')
def health_check_p():
    return "This datasource is healthy"

# return a list of data that can be queried
@app.route('/summary/search', methods=['POST'])
def search():
    count_set = set()
    for scan in db.listAllScans():
        count_set.add( "High" + "-" + scan['scanId'] )
        count_set.add( "Medium" + "-" + scan['scanId'] )
        count_set.add( "Low" + "-" +  scan['scanId'] )
        count_set.add( "Informational" + "-" + scan['scanId'] )
    return jsonify( list(count_set) )

@app.route('/progress/search', methods=['POST'])
def search_p():
    progress_set = set()
    for scan in db.listAllScans():
        progress_set.add( "Passive_Scan_Progress" + "-" + scan['scanId'] )
        progress_set.add( "Active_Scan_Progress" + "-" + scan['scanId'] )
    return jsonify( list(progress_set) )

@app.route('/summary/query', methods=['POST'])
def query():
    req = request.get_json()
    target = req['targets'][0]['target']
    target_id = re.findall(r'\d*$',target)[0]
    try: 
        report = db.findHtml(target_id)['html']
        source = report.decode("utf-8")
        print("summary is extracted from DB.(with id {})".format(target_id))
    except Exception as err:
        print("summary can not extracted from DB. Because {}.".format(err))

    global High
    global Medium
    global Low
    global Informational

    #find high_count
    hr = re.search(r'<td><a href=\"#high\">High</a></td><td align=\"center\">(.*)</td>', source, flags=0)
    High[target_id] = int( hr.group(1) )

    #find medium_count
    mr = re.search(r'<td><a href=\"#medium\">Medium</a></td><td align=\"center\">(.*)</td>', source, flags=0)
    Medium[target_id] = int( mr.group(1) )
    
    #find low_count
    lr = re.search(r'<td><a href=\"#low\">Low</a></td><td align=\"center\">(.*)</td>', source, flags=0)
    Low[target_id] = int( lr.group(1) )

    #find informational_count
    ir = re.search(r'<td><a href=\"#info\">Informational</a></td><td align=\"center\">(.*)</td>', source, flags=0)
    Informational[target_id] = int( ir.group(1) )

    data = [
        {
            "target": "High" + "-" + str(target_id),
            "datapoints": [
                [High[target_id], 1563761410]
            ]
        },
        {
            "target": "Medium" + "-" + str(target_id),
            "datapoints": [
                [Medium[target_id],1563761410]
            ]
        },
        {
            "target": "Low" + "-" + str(target_id),
            "datapoints": [
                [Low[target_id], 1563761410]
            ]
        },
        {
            "target": "Informational" + "-" + str(target_id),
            "datapoints": [
                [Informational[target_id], 1563761410]
            ]
        }
    ]
    return jsonify(data)

@app.route('/progress/query', methods=['POST'])
def query_p():
    req = request.get_json()
    target = req['targets'][0]['target']
    target_id = re.findall(r'\d*$',target)[0]

    global Passive_Scan_Progress
    global Active_Scan_Progress
    Passive_Scan_Progress[target_id] = 0
    Active_Scan_Progress[target_id] = 0
    try:
        Passive_Scan_Progress[target_id] = int (db.findScan(target_id)["pscanStatus"])
        Active_Scan_Progress[target_id] = int (db.findScan(target_id)["ascanStatus"])
        print ("/progress/query: target_id={}".format(target_id) )
    except Exception as err:
        print ("fail to findScan in DB. Because {}".format(err))
    progress = [
            {
                "target": "Passive_Scan_Progress"+"-"+ str(target_id),
                "datapoints":[
                    [Passive_Scan_Progress[target_id], 1563761410]
                    ]
            },
            {
                "target": "Active_Scan_Progress"+"-"+ str(target_id),
                "datapoints":[
                    [Active_Scan_Progress[target_id], 1563761410]
                    ]
            }
    ]
    return jsonify(progress)

@app.route('/datasource/report/<scanId>', methods=['GET'])
@cross_origin()
def datasource_report(scanId):
    try: 
        report = db.findHtml(str(scanId))
        source = report['html'].decode("utf-8")
        print("report is extracted from DB.")
        head = source.split("<h1>",1)
        body = head[1].split("<h3>Alert Detail</h3>",1)
        html = "".join(head[0]+body[1])
        response = make_response(html,200)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as err:
        print("Report can not extracted from DB. Becasue {}".format(err))
        print("You're scanId is {}. Report not found".format(scanId))
        return "Report Not Found"