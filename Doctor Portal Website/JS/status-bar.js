/*
Project Name: WS2021_5 ; AsthmAlarm
Team Members: Emily Luo, Matthew Shen, Esben Nielsen, Pranavi Gollamudi
Date: 6/03/2021
Task Description: backend code for the status bar indicator at the bottom of the navbar, indicating 
    whether the current user is logged in or not
*/

firebase.auth().onAuthStateChanged(user => {
    if (user) {
        document.getElementById('sign-in-state').innerText = "Signed In";
    } else {
        document.getElementById('sign-in-state').innerText = "Signed Out";
    }
})

