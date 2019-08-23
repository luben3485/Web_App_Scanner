import sys
import re
import json
import requests
from flask_cors import cross_origin

from datasource_route import High, Medium, Low, Informational
from datasource_route import Passive_Scan_Progress, Active_Scan_Progress

def datasource_init(appURL,apiURL,scanId):
    global High, Medium, Low, Informational, Passive_Scan_Progress, Active_Scan_Progress
    High[scanId] = 0
    Medium[scanId] = 0
    Low[scanId] = 0
    Informational[scanId] = 0
    Passive_Scan_Progress[scanId] = 0    
    Active_Scan_Progress[scanId] = 0
def create_dashboard(appURL,apiURL,scanId, EIToken):
    my_headers = {'Content-Type':'application/json','Authorization': 'Bearer {}'.format(EIToken)}
    try:
        with open('template.json') as json_file:
            template = json.load(json_file)
        payload ={
            "dashboard": template,
            "folderId": 0,
            "overwrite": False
        }
        template["uid"] = scanId
        template["title"] = template["title"] + "-" + str(scanId)
        template["panels"][0]["datasource"] = "ZAP-Progress"
        template["panels"][1]["datasource"] = "ZAP-Summary"
        template["panels"][2]["datasource"] = "ZAP-Summary"

        template["panels"][0]["targets"][0]["target"] = "Passive_Scan_Progress"+"-"+str(scanId)
        template["panels"][0]["targets"][1]["target"] = "Active_Scan_Progress"+"-"+str(scanId)
        
        template["panels"][1]["targets"][0]["target"] = "High"+"-"+str(scanId)
        template["panels"][1]["targets"][1]["target"] = "Medium"+"-"+str(scanId)
        template["panels"][1]["targets"][2]["target"] = "Low"+"-"+str(scanId)
        template["panels"][1]["targets"][3]["target"] = "Informational"+"-"+str(scanId)
        template["panels"][1]["aliasColors"] = {
            "High"+"-"+str(scanId): "#bf1b00",
            "Medium"+"-"+str(scanId): "#e0752d",
            "Low"+"-"+str(scanId): "#f2c96d",
            "Informational"+"-"+str(scanId): "#7eb26d"
        }

        template["panels"][2]["targets"][0]["target"] = "High" +"-"+str(scanId)
        template["panels"][2]["targets"][0]["target"] = "Medium"+"-"+str(scanId)
        template["panels"][2]["targets"][0]["target"] = "Low"+"-"+str(scanId)
        template["panels"][2]["targets"][0]["target"] = "Informational"+"-"+str(scanId)
        template["panels"][4]["content"] = '''
        <html>
            <head>
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/semantic-ui/1.11.8/semantic.min.css"/>
            </head>
            <body>
            <button id="downloadReport" class="ui  blue button" style="font-size:1.3rem;">
                    <i class="file alternate outline icon"></i>
                    Download
                </button>
            
                
                <!--<script src="https://code.jquery.com/jquery-3.4.1.min.js"></script>-->
                <script>
                    $(document).ready(function(){
                        function getCookie(cname) {
                            var name = cname + "=";
                            var decodedCookie = decodeURIComponent(document.cookie);
                            var ca = decodedCookie.split(';');
                            for(var i = 0; i <ca.length; i++) {
                                var c = ca[i];
                                while (c.charAt(0) == ' ') {
                                    c = c.substring(1);
                                }
                                if (c.indexOf(name) == 0) {
                                    return c.substring(name.length, c.length);
                                }
                            }
                            return "";
                        }
                        function getScanId(){
                        var url = window.location.toString();
                        var tmp1 =url.split("web-app-scanner-")[1];
                        var tmp2 = tmp1.split("?")[0]
                        return tmp2;
                        
                        }
                        $('#downloadReport').click(function(){
                            scanId = getScanId();
                            appUrl = getCookie('appUrl');
                            $.ajax({
                                url: appUrl+'/downloadHtml',
                                method: 'GET',
                                data:{'scanId':scanId}
                            }).done(function (res) {
                                if(res=='fail'){
                                    console.log('now u cannot download report');
                                }else{
                                    var a = document.createElement('a');
                                    var url = window.URL.createObjectURL(new Blob([res], {type: "application/html"}));
                                    a.href = url;
                                    a.download = 'scan_report.html';
                                    document.body.append(a);
                                    a.click();
                                    a.remove();
                                    window.URL.revokeObjectURL(url);
                                }
                            }).fail(function () {
                                console.log("/downloadHtml fail") 
                            });
                            
                        });
                        function getCookie(cname) {
                            var name = cname + "=";
                            var decodedCookie = decodeURIComponent(document.cookie);
                            var ca = decodedCookie.split(';');
                            for(var i = 0; i <ca.length; i++) {
                                var c = ca[i];
                                while (c.charAt(0) == ' ') {
                                    c = c.substring(1);
                                }
                                if (c.indexOf(name) == 0) {
                                    return c.substring(name.length, c.length);
                                }
                            }
                            return "";
                        }
                        
                        
                    });
                </script>
            
            </body>
        </html>
        '''
        #Above is Button.
        template["panels"][5]["url"] = appURL+'/datasource/report/'+str(scanId) #for new template
        
        res = requests.post(apiURL + "/api/dashboards/db", headers=my_headers, json=payload)
        print( res.text )
        dashboardLink = apiURL +res.json()["url"]
        datasource_init(appURL,apiURL,scanId)
        return dashboardLink
    except Exception:
        raise
def delete_dashboard(appURL,apiURL,scanId, EIToken):
    my_headers = {'Content-Type':'application/json',
               'Authorization': 'Bearer {}'.format(EIToken)}
    res = requests.delete(apiURL + "/api/dashboards/uid/" + scanId, headers=my_headers)
    res_json = res.json()
    print( res_json["title"]+" has been deleted." )
    return res.json()