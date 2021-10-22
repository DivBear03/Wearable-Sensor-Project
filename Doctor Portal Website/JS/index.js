/*
Project Name: WS2021_5 ; AsthmAlarm
Team Members: Emily Luo, Matthew Shen, Esben Nielsen, Pranavi Gollamudi
Date: 6/03/2021
Task Description: Backend code for index.js
Functions:
1. Populates the patient cards on the right hand side of the screen
2. Tracks the authentication status of the user and hides buttons according to their login status
3. Handles form submissions from the login modal, the doctor registration modal, and the patient registration modal
*/

var currentUser;
function removePeriods(input) {
  return input.replace(/\./g, "_()");
}
function addPeriods(input) {
  return input.replace(/\_\(\)/g, ".");
}

//listen for auth status changes
firebase.auth().onAuthStateChanged(user => {
  if (user) {
      console.log("User logged in: ", user);
      currentUser = user;
      populateElements();
      document.getElementById('patient-reg').style.display = 'block';
      document.getElementById('patient-info').style.display = 'block';
      document.getElementById('logout').style.display = 'block';
      document.getElementById('login').style.display = 'none';
      document.getElementById('register').style.display = 'none';
  } else {
      console.log("User logged out");
      currentUser = null;
      document.getElementById('patient-reg').style.display = 'none';
      document.getElementById('patient-info').style.display = 'none';
      document.getElementById('logout').style.display = 'none';
      document.getElementById('login').style.display = 'block';
      document.getElementById('register').style.display = 'block';
  }

})

const register_form = document.querySelector("#register-form")
register_form.addEventListener('submit', (e) => {
  e.preventDefault();
  const email = register_form['inputEmail'].value;
  const password = register_form['inputPassword'].value;
  const f_name = register_form['inputFName'].value;
  const l_name = register_form['inputLName'].value;
  const credentials = register_form['credentials'].value;
  const address = register_form['street_address'].value;
  const city = register_form['city'].value;
  const state = register_form['state'].value;
  const zip = register_form['zip'].value;
  if (email!="" && password!="" && f_name != "" && l_name!="" && credentials!="" && address!="" && city!="" && state!="" && zip!="") {
    if (email.match(/.*@.*\..*/) != null) {
      firebase.auth().createUserWithEmailAndPassword(email, password)
        .then((credential) => {
          currentUser = credential.user;
          alert("You have been registered and are now logged in");
          $("#registerModal").modal('toggle');
          firebase.database().ref("Users/" + removePeriods(email)).set({
            First_Name: f_name,
            Last_Name: l_name,
            Email: email,
            Credentials: credentials,
            Address: {
              Street_Address: address,
              City: city,
              State: state,
              Zip_Code: zip
            }
          })
        }).catch((e) => {
          console.log(e.message);
          alert(e.message);
        })
    } else {
      alert("Email must be formatted correctly");
    }
  } else {
    alert("All form fields must be filled out");
  }
})

const login_form = document.querySelector("#login-form");
login_form.addEventListener("submit", (e) => {
  e.preventDefault();
  const email = login_form['inputEmailLogin'].value;
  const password = login_form['inputPasswordLogin'].value;
  firebase.auth().signInWithEmailAndPassword(email, password)
    .then((credential) => {
      currentUser = credential.user;
      $("#loginModal").modal('toggle');
      alert("You are signed in");
    })
    .catch((e) => {
      console.log(e.message);
      alert(e.message);
    })
})

const patientRegForm = document.querySelector("#patientreg-form");
patientRegForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const email = patientRegForm['inputEmailpatient'].value;
  const f_name = patientRegForm['inputFNamePatient'].value;
  const l_name = patientRegForm['inputLNamePatient'].value;
  if (email != "" && f_name != "" && l_name != "") {
    if (email.match(/.*@.*\..*/) != null) {
      firebase.database().ref("Users/" + removePeriods(currentUser.email) + "/Patients/" + removePeriods(email)).set({
        Email: email,
        First_Name: f_name,
        Last_Name: l_name
      }).then(function() {
        $("#patientregModal").modal('toggle');
        alert("You have registered a patient");
        firebase.database().ref("Patients/" + removePeriods(email)).set({
          Sessions: {},
          Email: email
        })
      })
    } else {
      alert("Email format is incorrect");
    }
  } else {
    alert("All form fields must be filled in");
  }
})

//logout function
const logout = document.querySelector('#logout-btn');
logout.addEventListener('click', (e) => {
    e.preventDefault();
    firebase.auth().signOut();
    alert("You've been signed out");
});

function populateElements() {
  var parent = document.querySelector("#patient_cards");
  var data1;
  firebase.database().ref("Users/" + removePeriods(currentUser.email)).once('value', function(snapshot) {
    data1 = snapshot.val()['Patients'];
    
    document.getElementById("doc_email").innerText = snapshot.val()['Email'];
    document.getElementById("doc_cred").innerText = snapshot.val()['Credentials'];
    document.getElementById("doc_name").innerText = snapshot.val()['First_Name'] + " " + snapshot.val()['Last_Name'];
  }).then(function() {
    for (var patient in data1) {
      let lastSession;
      let newpatient = patient;
      firebase.database().ref("Patients/" + patient + "/Sessions").once('value', function(snapshot) {
          const data2 = snapshot.val();
          for(i in data2) {
            lastSession = i;
          }
          let newCard = document.createElement("div");
          newCard.classList.add("card");
          let newHeader = document.createElement("h5");
          newHeader.classList.add('card-header');
          newHeader.innerText = data1[newpatient]['First_Name'] + " " + data1[newpatient]['Last_Name'];
    
          let newBody = document.createElement('div');
          newBody.classList.add("card-body");
          if (lastSession != null) {
            let newText = document.createElement("p");
            newText.classList.add("card-text");
            newText.innerText = "Last Session: " + lastSession.split(" ")[0];
            newBody.appendChild(newText);
          }
          let anchor = document.createElement("a");
          anchor.classList.add("btn", "btn-primary");
          anchor.innerText = "See Patient Info";
          // anchor.href = "patient-info.html";
          let argument = removePeriods(newpatient);
          anchor.onclick = function() {
            setCurrentPatient(argument);
          }
          anchor.href = "patient-info.html";
          
          newBody.appendChild(anchor);
    
          newCard.appendChild(newHeader);
          newCard.appendChild(newBody);
          parent.appendChild(newCard);
      })   
    }
  })
}

function setCurrentPatient(email) {
  firebase.database().ref("Current_Patient").set({
    Current: email
  }).then(function() {})
}

const sendFeedback = document.getElementById("send-feedback-btn");
sendFeedback.addEventListener("click", function(e) {
  e.preventDefault();
  var email = document.getElementById("inputEmailFeedback").value;
  var feedback = document.getElementById("inputFeedback").value;
  var date = new Date();
  var dateString = String(date.getMonth() + 1) +"-"+ String(date.getDay()-1) +"-"+ String(date.getFullYear()) + " " + date.toLocaleTimeString()
  // console.log(date.getDate());
  console.log(dateString);
  if (email != "" && feedback != "") {
    firebase.database().ref("User_Feedback/" + dateString).set({
      Email: email,
      FeedbackMessage: feedback
    }).then(function() {
      alert("Feedback submitted. Thank you!");
    })
  } else {
    alert("All form fields must be filled in")
  }
})