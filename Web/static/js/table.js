var deleted=[];
var deletedFlag = 0;
var deletedSchedule = []
var deletedScheduleFlag = 0;
var Data = [];

var schedule =[];
$(document).ready(function(){
    
    $('#tab1').click(function(){
        $(this).addClass('active');
        $('#tab2').removeClass('active');
    });
    $('#tab2').click(function(){
        $(this).addClass('active');
        $('#tab1').removeClass('active');
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

function downloadHtml(scanId){
    var ssoUrl = getCookie('SSO_URL');
        $.ajax({
            url: ssoUrl + '/v2.0/users/me',
            method: 'GET',
            xhrFields: {
                withCredentials: true
            }
        }).done(function (user) {
             $.ajax({
                    url: '/downloadHtml',
                    method: 'GET',
                    data:{'scanId':scanId}
                }).done(function (res) {
                    if(res=='fail'){
                        
                        //console.log('now u cannot download report');
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
                    //console.log("/downloadHtml fail") 
                });         
        }).fail(function () {
            window.location.href = ssoUrl + '/web/signIn.html?redirectUri=' + myUrl;
            //console.log("download html fail") 
        });         
    
}


function deleteScans(scanIdArr){
    
    $.ajax({
                url: '/deleteScans',
                type: 'POST',
                 data: {
                    'scanIdArr':scanIdArr
                }
    }).done(function(){
        //console.log("delete scan success");
        var d=new Date();
        var timeZone = (d.getTimezoneOffset()>0?"-":"+") +(d.getTimezoneOffset()/-60);
        $.ajax({
                url: '/refreshTable',
                type: 'GET',
                data:{
                    'timeZone':timeZone
                }
        }).done(function(response){
            while (Data.length > 0) Data.pop();
            while (response.length > 0) Data.push(response.shift());
            //console.log("refresh table successfully")
        }).fail(function(){
            //console.log("refresh table fail") 
        });
        $.ajax({
                url: '/refreshScheduleTable',
                type: 'GET',
                data:{
                    'timeZone':timeZone
                }
        }).done(function(response){
            while (schedule.length > 0) schedule.pop();
            while (response.length > 0) schedule.push(response.shift());
            //console.log("refresh schedule table successfully")
        }).fail(function(){
            //console.log("refresh schedule table fail") 
        });
        
        
        
    }).fail(function(){
        
        //console.log("delete scan error");
        
    });

    
}
    
var Main ={
        data() {
            return {
                tab:2,
                isLoading: true,
                tables1: {
                    tableData: Data,
                    columns: [
                        {width: 50, titleAlign: 'center',columnAlign:'center',type: 'selection' 
                        },
                        {
                            field: 'custome', title:'Number', width: 40, titleAlign: 'center', columnAlign: 'center',
                            formatter: function (rowData,rowIndex,pagingIndex,field) {
                                return rowIndex >=0 ? '<span style="color:#000000;font-weight: bold;">' + (rowIndex + 1) + '</span>' : rowIndex + 1
                            }, isFrozen: true,isResize:true
                        },
                        {field: 'targetURL', title:'Target URL', width: 250, titleAlign: 'center',columnAlign:'center',isResize:true},
                        {field: 'time', title: 'Time', width: 100, titleAlign: 'center',columnAlign:'center',isResize:true},
                        {field: 'dashboard', title: 'Dashboard', width: 40, titleAlign: 'center',columnAlign:'center',componentName:'table-dashboard',isResize:true},
                        {field: 'custome-adv', title: 'Operation',width: 120, titleAlign: 'center',columnAlign:'center',componentName:'table-operation',isResize:true}
                    ]
                },
                
                tables2: {
                    tableData: schedule,
                    columns: [
                        {width: 50, titleAlign: 'center',columnAlign:'center',type: 'selection' 
                        },
                        {
                            field: 'custome', title:'Number', width: 40, titleAlign: 'center', columnAlign: 'center',
                            formatter: function (rowData,rowIndex,pagingIndex,field) {
                                return rowIndex >=0 ? '<span style="color:#000000;font-weight: bold;">' + (rowIndex + 1) + '</span>' : rowIndex + 1
                            }, isFrozen: true,isResize:true
                        },
                        {field: 'userName', title:'User name', width: 90, titleAlign: 'center',columnAlign:'center',isResize:true},
                        {field: 'targetURL', title:'Target URL', width: 250, titleAlign: 'center',columnAlign:'center',isResize:true},
                        {field: 'time', title: 'Time', width: 150, titleAlign: 'center',columnAlign:'center',isResize:true},
                        {field: 'period', title: 'Period', width: 50, titleAlign: 'center',columnAlign:'center',isResize:true},
                        {field: 'custome', title: 'Operation',width: 100, titleAlign: 'center',columnAlign:'center',componentName:'schedule-operation',isResize:true}
                    ]
                
                }

            }
        },
        methods:{
            selectALL(selection){
                
                //console.log('select-aLL',selection);
                if(selection.length !=0){
                    deletedFlag = 1;
                    while (deleted.length > 0) deleted.pop();
                    selection.forEach(function(item, index, array){
                        deleted.push(index);
                    });
                    //console.log('deleted:'+deleted)
                }else{
                    deletedFlag = 0;
                }
            },
            selectChange(selection,rowData){
                //console.log('select-change',selection,rowData);
                
            },

            selectGroupChange(selection){
                deletedFlag = 1;
                //console.log('select-group-change',selection);
                while (deleted.length > 0) deleted.pop();
                selection.forEach(function(item, index, array){
                    for(var i=0;i<Data.length;i++){
                        if(Data[i].scanId == item.scanId){
                            deleted.push(i);
                        }   
                        
                    }

                });
                //console.log('deleted:'+deleted)
                    
            },selectALLSchedule(selection){
                
                //console.log('select-aLL',selection);
                if(selection.length !=0){
                    deletedScheduleFlag = 1;
                    while (deletedSchedule.length > 0) deletedSchedule.pop();
                    selection.forEach(function(item, index, array){
                        deletedSchedule.push(index);
                    });
                    //console.log('deleted:'+deletedSchedule)
                }else{
                    deletedScheduleFlag = 0;
                }
            },selectGroupChangeSchedule(selection){
                deletedScheduleFlag = 1;
                //console.log('select-group-change',selection);
                while (deletedSchedule.length > 0) deletedSchedule.pop();
                selection.forEach(function(item, index, array){
                    for(var i=0;i<schedule.length;i++){
                        if(schedule[i].scanId == item.scanId){
                            deletedSchedule.push(i);
                        }   
                        
                    }

                });
                //console.log('deleted:'+deletedSchedule)
                    
            },
            customCompFunc(params){

                //console.log(params);

                if (params.type === 'delete1'){ // do delete operation
                    deleteScans([params.rowData['scanId']]);
                    //this.$delete(this.tables1.tableData,params.index);

                }else if (params.type === 'delete2'){ // do delete operation
                    deleteScans([params.rowData['scanId']]);
                    //this.$delete(this.tables2.tableData,params.index);
                    
                }else if (params.type === 'download'){ // do download operation
                    /*
                    alert(`Number：${params.index} Target URL：${params.rowData['targetURL']}  time：${params.rowData['time']}  scanId：${params.rowData['scanId']}`)
                    */
                    scanId = params.rowData['scanId'];
                    //userId = params.rowData['userId'];    
                    downloadHtml(scanId);

                }else if (params.type === 'dashboard'){ // do download operation
                    
                    //dashboard link
                    window.open(params.rowData['dashboardLInk']);
                    //window.location.href = params.rowData['dashboardLInk'];
                }

            },
            remove(){
                //alert(this.tableData[0]['targetURL']);
                //var index = this.tableData.indexof(this.tableData);
                //this.tableData.splice(index,1)

                if(deletedFlag == 1){
                    var scanIdArr = [];
                    deleted.forEach(function(element, index){
                        scanIdArr.push(Data[element]['scanId']);
                        
                    });
                    deleteScans(scanIdArr)
                    //alert(scanIdArr);
                    
                    deletedFlag = 0;
                }else if(deletedScheduleFlag == 1){
                    var scanIdArr = [];
                    deletedSchedule.forEach(function(element, index){
                        scanIdArr.push(schedule[element]['scanId']);
                        
                    });
                    deleteScans(scanIdArr)
                    //alert(scanIdArr);
                    deletedScheduleFlag = 0;
                    //alert('no');
                }
                    
                
                
                
            },
            tabClick(tabId){
                 this.tab = tabId;
                 this.$refs['table'+tabId].resize();

            }
        }
    }

    Vue.component('table-dashboard',{
        template:`<span>
        <!--<button id="dashboardlink" style="font-size:1rem;width:auto;" class="ui  green  button" @click.stop.prevent="update(rowData,index)">
            <i class="external alternate icon"></i>
            
        </button>--> 
        <a href="" @click.stop.prevent="dashboardLink(rowData,index)">Link</a>
        </span>`,
        props:{
            rowData:{
                type:Object
            },
            field:{
                type:String
            },
            index:{
                type:Number
            }
        },
        methods:{
            dashboardLink(){

               let params = {type:'dashboard',index:this.index,rowData:this.rowData};
               this.$emit('on-custom-comp',params);
            }
        }
    })


    Vue.component('table-operation',{
        template:`<span>
        <a href="" @click.stop.prevent="download(rowData,index)">Download</a>&nbsp;&nbsp;&nbsp;&nbsp;
        <a href="" @click.stop.prevent="deleteRow(rowData,index)">Delete</a>
        </span>`,
        props:{
            rowData:{
                type:Object
            },
            field:{
                type:String
            },
            index:{
                type:Number
            }
        },
        methods:{
            download(){

               let params = {type:'download',index:this.index,rowData:this.rowData};
               this.$emit('on-custom-comp',params);
            },

            deleteRow(){

                let params = {type:'delete1',index:this.index,rowData:this.rowData};
                this.$emit('on-custom-comp',params);

            }
        }
    })

    
    Vue.component('schedule-operation',{
        template:`<span>
        <a href="" @click.stop.prevent="deleteRow(rowData,index)">Delete</a>
        </span>`,
        props:{
            rowData:{
                type:Object
            },
            field:{
                type:String
            },
            index:{
                type:Number
            }
        },
        methods:{
            deleteRow(){
                
                let params = {type:'delete2',index:this.index,rowData:this.rowData};
                this.$emit('on-custom-comp',params);

            }
        }
    })

var Ctor = Vue.extend(Main)
new Ctor().$mount('#app')







