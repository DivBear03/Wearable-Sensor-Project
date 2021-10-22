/*
Project Name: WS2021_5 ; AsthmAlarm
Team Members: Emily Luo, Matthew Shen, Esben Nielsen, Pranavi Gollamudi
Date: 6/03/2021
Task Description: Backend code for patient-info.js
Functions:
1. Tracks the authentication status of the current user, and hides buttons on the navbar accordingly
2. Handles the displaying of the selected data from the dropdown menus with the JSCharting library
3. Populates the dropdown menus according to the sensor sessions logged in firebase
4. Handles any edits that the doctor makes to their patient's sensor configuration metrics, such as standard 
    deviation threshold, the standard deviation calculation look back time, and the logging interval
*/

var currentUser;
function removePeriods(input) {
  return input.replace(/\./g, "_()");
}
function addPeriods(input) {
  return input.replace(/\_\(\)/g, ".");
}
function removeAllChildNodes(parent) {
    while (parent.firstChild) {
        parent.removeChild(parent.firstChild);
    }
}
//listen for auth status changes
firebase.auth().onAuthStateChanged(user => {
  if (user) {
      console.log("User logged in: ", user);
      currentUser = user;
      populateDropdown();
      document.getElementById('patient-reg').style.display = 'block';
      document.getElementById('patient-info').style.display = 'block';
      document.getElementById('logout').style.display = 'block';
      document.getElementById('login').style.display = 'none';
      document.getElementById('register').style.display = 'none';
  } else {
      console.log("User logged out");
      currentUser = null;
      window.location.replace("index1.html");
      document.getElementById('patient-reg').style.display = 'none';
      document.getElementById('patient-info').style.display = 'none';
      document.getElementById('logout').style.display = 'none';
      document.getElementById('login').style.display = 'block';
      document.getElementById('register').style.display = 'block';
      window.location.replace("index.html");
  }

})

const patientSelect = document.querySelector("#patientselect");
patientSelect.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = patientSelect['patient-select'].value;
    const session = patientSelect['session-select'].value;
    firebase.database().ref("Patients/" + removePeriods(email) + "/Sessions/" + session).once('value', function(snapshot) {
        const data = snapshot.val()['Data'];
        console.log(data);
        if (snapshot.val()['ContainsSTDEV'] == "True") {
            var points = [];
            var stdevPoints = [];
            var thresholdpoints = [];
            for (i in data) {
                points.push({x: Number(addPeriods(i)), y: Number(String(data[i]).split(";;;")[0])})
                stdevPoints.push({x: Number(addPeriods(i)), y: Number(String(data[i]).split(";;;")[1])})
                thresholdpoints.push({x: Number(addPeriods(i)), y: snapshot.val().Configuration.Threshold})
            }
            //Insertion sort for the points list and stdevPoints list
            for (var i = 0; i < points.length; i++ ){
                var min = points[i]['x'];
                var minObj = points[i];
                var minID = i;
                for (var j = i + 1; j < points.length; j++) {
                    if (points[j]['x'] < min) {
                        min = points[j]['x'];
                        minObj = points[j];
                        minID = j;
                    }
                }
                var temp = points[i];
                points[i] = minObj;
                points[minID] = temp;
            }
            for (var i = 0; i < stdevPoints.length; i++ ){
                var min = stdevPoints[i]['x'];
                var minObj = stdevPoints[i];
                var minID = i;
                for (var j = i + 1; j < stdevPoints.length; j++) {
                    if (stdevPoints[j]['x'] < min) {
                        min = stdevPoints[j]['x'];
                        minObj = stdevPoints[j];
                        minID = j;
                    }
                }
                var temp = stdevPoints[i];
                stdevPoints[i] = minObj;
                stdevPoints[minID] = temp;
            }
            renderChartStdev([{name: "EMG_value", points: points}, {name: "Standard Deviation", points: stdevPoints}, {name: "Alarm Threshold", points: thresholdpoints}], session);
        } else {
            var points = [];
            for (i in data) {
                points.push({x: Number(addPeriods(i)), y: Number(data[i])})
            }
            //Insertion sort for the points list
            for (var i = 0; i < points.length; i++ ){
                var min = points[i]['x'];
                var minObj = points[i];
                var minID = i;
                for (var j = i + 1; j < points.length; j++) {
                    if (points[j]['x'] < min) {
                        min = points[j]['x'];
                        minObj = points[j];
                        minID = j;
                    }
                }
                var temp = points[i];
                points[i] = minObj;
                points[minID] = temp;
            }
            renderChartNoStdev([{name: "EMG_value", points: points, options: {
                line: {
                    dashStyle: "dot",
                    caps: {
                        end_type: "arrow",
                        start_type: "circle"
                    }
                }
            }}], session);
        }
        document.getElementById("send_rate_left_side").innerText = snapshot.val()['Configuration']['SendRate'] + " ms";
        document.getElementById("look_back_left_side").innerText = snapshot.val()['Configuration']['LookBackTime'] + " seconds";
        document.getElementById("thresh_left_side").innerText = snapshot.val()['Configuration']['Threshold'] + " V";
        document.getElementById("datem_left_side").innerText = snapshot.val()['DateTime'];
    })
})

function renderChartNoStdev(series, session) {
	JSC.Chart('chartDiv', {
		series: series,
        title_label_text: session + ": EMG Value (V) vs Time (s)",
        legend_visible: false,
        defaultSeries_lastPoint_label_text: '<b>%seriesName</b>',
        xAxis_crosshair_enabled: true,
        xAxis_label_text: "Time Since Start (s)",
        yAxis_label_text: "EMG Value (V)",
	});
}

function renderChartStdev(series, session) {
    var chart = JSC.Chart('chartDiv', {
        series: series, 
        title_label_text: session + ": EMG Value (V) vs Time (s)",
        legend_visible: false,
        defaultSeries_lastPoint_label_text: "<b>%seriesName</b>",
        xAxis_crosshair_enabled: true,
        xAxis_label_text: "Time Since Start (s)",
        yAxis_label_text: "EMG Value (V)"
    })
    chart.series(2).options({
        line: {
            dashStyle: "dot",
            
        },
        defaultPoint_marker: {
            size: 0
        }
    })
    chart.series(1).options({
        defaultPoint_marker: {
            size: 4
        }
    })
}

function populateDropdown() {
    var current_email;
    var patientSelection = document.querySelector("#patient-select");
    firebase.database().ref("Current_Patient").once('value', function(snapshot) {
        current_email = snapshot.val().Current;
    }).then(function() {
        firebase.database().ref("Users/" + removePeriods(currentUser.email) + "/Patients").once('value', function(snapshot) {
            const data = snapshot.val();
            for (i in data){
                var newOption = document.createElement('option');
                newOption.value = i;
                newOption.innerText = data[i].First_Name + " " + data[i].Last_Name;
                if (removePeriods(data[i].Email) === current_email) {
                    newOption.selected = true;
                    
                }
                patientSelection.appendChild(newOption);
            }
            populateSessions();
        })
    })     
}

function populateSessions(){
    var sessionSelection = document.querySelector("#session-select");
    const email = patientSelect['patient-select'].value;
    firebase.database().ref("Patients/" + removePeriods(email) + "/Sessions").once('value', function(snapshot) {
        const data = snapshot.val();
        if (data != null) {
            for (session in data) {
                var newOption = document.createElement('option');
                newOption.value = session;
                newOption.innerText = session;
                sessionSelection.appendChild(newOption);
            }
        } else {
            removeAllChildNodes(sessionSelection);
            document.getElementById("sendrate").textContent = "";
            document.getElementById("stdev_lookback").textContent = "";
            document.getElementById("stdev_thresh").textContent = "";
        }
    })
    firebase.database().ref("Patients/" + removePeriods(email) + "/Configuration").once('value', function(snapshot) {
        const data = snapshot.val();
        if (data != null) {
            document.getElementById("sendrate").textContent = String(data["Send_Rate"]) + " ms";
            document.getElementById("stdev_lookback").textContent = String(data["StDevLookBack"]) + " seconds";
            document.getElementById("stdev_thresh").textContent = String(data['Stdev_Thresh']) + " V";
            document.getElementById("new_sendrate").value = data["Send_Rate"];
            document.getElementById("new_stdev_lookback").value = data["StDevLookBack"];
            document.getElementById("new_stdev_thresh").value = data['Stdev_Thresh'];
        }
    })
    firebase.database().ref("Current_Patient").set({
        Current: removePeriods(email)
    })
    
}

function changeSendRate() {
    var newRate = document.getElementById("new_sendrate").value;
    var patientEmailToChange = document.getElementById("patient-select").value;
    firebase.database().ref("Patients/" + patientEmailToChange + "/Configuration").set({
        Send_Rate: Number(newRate),
        StDevLookBack: Number(document.getElementById("stdev_lookback").innerText.replace(" seconds", "")),
        Stdev_Thresh: Number(document.getElementById("stdev_thresh").innerText.replace(" V", ""))
    }).then(function() {
        populateSessions();
    })
}

function changeLookBack() {
    var newLookBack = document.getElementById("new_stdev_lookback").value;
    var patientEmailToChange = document.getElementById("patient-select").value;
    firebase.database().ref("Patients/" + patientEmailToChange + "/Configuration").set({
        Send_Rate: Number(document.getElementById("sendrate").innerText.replace(" ms", "")),
        StDevLookBack: Number(newLookBack),
        Stdev_Thresh: Number(document.getElementById("stdev_thresh").innerText.replace(" V", ""))
    }).then(function() {
        populateSessions();
    })
}

function changeThreshold() {
    var newThresh = document.getElementById("new_stdev_thresh").value;
    var patientEmailToChange = document.getElementById("patient-select").value;
    firebase.database().ref("Patients/" + patientEmailToChange + "/Configuration").set({
        Send_Rate: Number(document.getElementById("sendrate").innerText.replace(" ms", "")),
        StDevLookBack: Number(document.getElementById("stdev_lookback").innerText.replace(" seconds", "")),
        Stdev_Thresh: Number(newThresh)
    }).then(function() {
        populateSessions();
    })
}

//logout function
const logout = document.querySelector('#logout-btn');
logout.addEventListener('click', (e) => {
    e.preventDefault();
    firebase.auth().signOut();
    alert("You've been signed out");
});

/* const fetch = require("");
console.log("got node-fetch");
const ipaddressInput = document.getElementById("ip_address");
document.getElementById("ip_submit").addEventListener('click', function(e) {
    e.preventDefault();
    var ip = ipaddressInput.value;
    console.log("Sent IP: " + ip);
    fetch("https://" + ip + ":5000/GET /?IPAddress=" + ip);
    
}) */


/* const ipaddressInput = document.getElementById("ip_address");
document.getElementById("ip_submit").addEventListener('click', function(e) {
    let email = "magnuscarlsen@gmail_()com"
    let http = new XMLHttpRequest();
    http.open('get', 'http://' + String(ipaddressInput.value) + ':5000/?Email=' + email);
    http.send();
    http.onload = function() {
        console.log(http.response);
    };
}) */