"""
Project Name: WS2021_5 ; AsthmAlarm
Team Members: Emily Luo, Matthew Shen, Esben Nielsen, Pranavi Gollamudi
Date: 6/03/2021
Task Description: Test file for EXE conversion using pyrebase
    Used as a debugging platform for the auto-py-to-exe tool
"""

import pyrebase
import time
config = {
    "apiKey": "AIzaSyCe9YmRHZIV3RdGZOzBUBsrP3EMjLPYKx4",
    "authDomain": "asthmalarm.firebaseapp.com",
    "databaseURL": "https://asthmalarm.firebaseio.com",
    "storageBucket": "asthmalarm.appspot.com"
    }
# Firebase reference app
firebaseref = pyrebase.initialize_app(config)
def removePeriods(input):
    while input.__contains__("."):
        input = input.replace(".", "_()")
    return input
patient_email = "magnuscarlsen@gmail.com"
time.sleep(3)
input("Starting first request")
print(firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Configuration").get().val())
input()
sendrate = int(dict(firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Configuration").get().val())['Send_Rate'])
input()
stdev_thresh = float(dict(firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Configuration").get().val())['Stdev_Thresh'])
input()
stdevlookbacktime = int(dict(firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Configuration").get().val())['StDevLookBack'])
input()
stdevlookbackpoints = stdevlookbacktime / (sendrate / 1000)
input()