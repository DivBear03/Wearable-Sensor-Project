"""
Project Name: WS2021_5 ; AsthmAlarm
Team Members: Emily Luo, Matthew Shen, Esben Nielsen, Pranavi Gollamudi
Date: 6/03/2021
Task Description: Develop a user-friendly application for interacting with the AsthmAlarm sensor that has the following functions:
    1. Displays real-time data from the sensor
    2. Hosts a Flask server for the sensor to send data to
    3. Allows for data to be saved to firebase and locally on the user's computer
    4. Allow for customized configuration of sensor parameters:
        1. Logging interval
        2. Standard deviation alarm threshold
        3. The number of seconds to take into account when calculating running standard deviation
    5. Can be packaged into an EXE file for ease of use
"""
#Libraries needed for hiding flask console output
import win32gui
import win32con

#hides the console when the windows bat file is run, only showing the tkinter gui in the long run
# the_program_to_hide = win32gui.GetForegroundWindow()
# win32gui.ShowWindow(the_program_to_hide , win32con.SW_HIDE)
import serial
import json
import os
#tkinter as tk and constants
import tkinter as tk
from tkinter.constants import *
from tkinter import filedialog
from tkinter import messagebox
#Multi threading library for running flask and tkinter and mpl at the same time
import _thread
#Time for detecting the start time of recording data
import time
#For inputting to firebase
from datetime import datetime
import pyrebase
#For running the HTTP server that will be accepting data from the Arduino
from flask import Flask
from flask import request
#For detecting the IP address at the location
import socket
#For graphing on a tkinter gui
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# For standard deviation calculation
import statistics
#For resizing images for the buttons
from PIL import Image
# For playing the alarm to wake the patient up
from playsound import playsound

import re

#Global variables for data, firebase database reference, initialTime
global x, y, firebase_data, firebaseref, initialTime, recvX, recvY, pastPoints, stdevData
global sendrate, networks, ConfigDict, stdev_thresh, stdevlookbacktime, stdevlookbackpoints, ip_address, patient_email
#Whether data will be recorded or not
global accepting
#Tkinter labels for displaying data as it comes in
global data1key, data1value, data2key, data2value, data3key, data3value, data4key, data4value, data5key, data5value
global data6key, data6value
# Signal bar images
global signal1, signal2, signal3, signal4
#Frame for showing the matplotlib graph
global graph_frame, toolbar, canvas
global graph_panel
global serial_port
global arduino_label, arduino_icon, redSig, greenSig, GUIStart, arduino_conn
#Holds the timestamps of data coming in
x = []
recvX = []
#Holds the EMG values
y = []
recvY = []
pastPoints = []
stdevData = []
#Json object holding both x and y
firebase_data = {}
#Firebase config
config = {
    "apiKey": "AIzaSyCe9YmRHZIV3RdGZOzBUBsrP3EMjLPYKx4",
    "authDomain": "asthmalarm.firebaseapp.com",
    "databaseURL": "https://asthmalarm.firebaseio.com",
    "storageBucket": "asthmalarm.appspot.com"
    }
# Firebase reference app
firebaseref = pyrebase.initialize_app(config)
global email_list
email_list = []

# Start with default of not accepting data
accepting = False

first = True
# Tkinter root
root = tk.Tk()
root.title("AsthmAlarm for Windows")

GUIStart = time.time()

arduino_conn = False

def removePeriods(input):
    while input.__contains__("."):
        input = input.replace(".", "_()")
    return input

def addPeriods(input):
    while input.__contains__("_()"):
        input = input.replace("_()", ".")
    return input

def openNewUser():
    global patient_email, ConfigDict
    inputWin = tk.Toplevel(root)
    inputWin.geometry("200x200")
    inputWin.resizable(0, 0)

    entryvalue = tk.StringVar()
    entry = tk.Entry(inputWin, textvariable = entryvalue)
    entry.place(relx = 0.5, rely = 0.25, anchor = CENTER)

    label = tk.Label(inputWin, text = "Enter your patient account \nemail address here", font = ("Helvetica", 10))
    label.place(relx = 0.5, rely = 0.45, anchor = CENTER)

    errortext = tk.Label(inputWin, text = "", font = ("Helvetica", 8), fg="red")
    errortext.place(relx = 0.5, rely = 0.9, anchor = CENTER)

    def newPatientEmail(input):
        global patient_email, ConfigDict, email_list
        print(input)
        if input not in email_list:
            errortext['text'] = "Patient Account does not exist. Try again"
            return
        if re.search(".+@.+\..+", input) == None:
            errortext['text'] = "Email Address is not valid. Try again"
            return
        patient_email = input
        ConfigDict['PatientAccount'] = patient_email
        inputWin.destroy()
        
    save_btn = tk.Button(inputWin, text = "Save", command = lambda: newPatientEmail(entryvalue.get()))
    save_btn.place(relx = 0.5, rely = 0.8, anchor = CENTER)

with open(os.path.dirname(os.path.realpath(__file__)) + "\\" + "config.json") as confighandle:
    ConfigDict = dict(json.loads(confighandle.read()))
    networks = ConfigDict['Wifi_Info']
    patient_email = ConfigDict['PatientAccount']
    if patient_email == "":
        root.after(1000, openNewUser)

# Getting configuration data from firebase
if patient_email != "":
    try:
        sendrate = int(dict(firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Configuration").get().val())['Send_Rate'])
        stdev_thresh = float(dict(firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Configuration").get().val())['Stdev_Thresh'])
        stdevlookbacktime = int(dict(firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Configuration").get().val())['StDevLookBack'])
        stdevlookbackpoints = stdevlookbacktime / (sendrate / 1000)
    except:
        messagebox.showerror("No internet connection. Connect to the internet and start AsthmAlarm again")
        quit()
else:
    sendrate = 500
    stdev_thresh = 0.06
    stdevlookbacktime = 20
    stdevlookbackpoints = stdevlookbacktime / (sendrate / 1000)

# Main function; runs once
def main():
    
    global data1key, data1value, data2key, data2value, data3key, data3value, data4key, data4value, data5key, data5value, data6key, data6value
    global graph_frame, graph_panel
    global signal1, signal2, signal3, signal4
    global arduino_label, arduino_icon, redSig, greenSig, arduino_status, email_list
    # Start the flask server on a separate thread
    _thread.start_new_thread(runFlask, ())

    patient_obj = firebaseref.database().child("Patients").get()
    for i in patient_obj.val():
        email_list.append(addPeriods(i))

    # Lock the window and disable a person's ability to close it normally, must use the tkinter button
    root.geometry("900x650")
    root.resizable(False, False)
    root.wm_protocol("WM_DELETE_WINDOW", disable_event)

    # canvas for displaying images in various places on the screen
    graph_panel = tk.Canvas(root, height = 600, width = 900)
    graph_panel.place(relx = 0.5, rely = 0.5, anchor = 'c')
    
    # Resizing the server image, placing it on the canvas
    resize_Image("server_icon.png", "server_icon.png", (40, 40))
    server_img_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "server_icon.png"
    server_img = tk.PhotoImage(file = server_img_dir)
    graph_panel.create_image(585, 530, image = server_img, anchor = 'nw')

    resize_Image("Signal Bar 1.png", "signal1.png", (40, 40))
    signal1_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "signal1.png"
    signal1Tk = tk.PhotoImage(file = signal1_dir)
    signal1 = graph_panel.create_image(620, 540, image = signal1Tk, anchor = 'nw', state = HIDDEN)

    resize_Image("Signal Bar 2.png", "signal2.png", (40, 40))
    signal2_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "signal2.png"
    signal2Tk = tk.PhotoImage(file = signal2_dir)
    signal2 = graph_panel.create_image(630, 536, image = signal2Tk, anchor = 'nw', state = HIDDEN)

    resize_Image("Signal Bar 3.png", "signal3.png", (40, 40))
    signal3_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "signal3.png"
    signal3Tk = tk.PhotoImage(file = signal3_dir)
    signal3 = graph_panel.create_image(640, 532, image = signal3Tk, anchor = 'nw', state = HIDDEN)

    resize_Image("Signal Bar 4.png", "signal4.png", (40, 40))
    signal4_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "signal4.png"
    signal4Tk = tk.PhotoImage(file = signal4_dir)
    signal4 = graph_panel.create_image(650, 528, image = signal4Tk, anchor = 'nw', state = HIDDEN)

    
    # Green status and red status circles
    resize_Image("green_status.png", "green_status.png", (30, 30))
    green_signal_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "green_status.png"
    greenSignalTk = tk.PhotoImage(file = green_signal_dir)
    greenSig = graph_panel.create_image(783, 550, image = greenSignalTk, anchor = 'c', state = HIDDEN)

    resize_Image("red_status.png", "red_status.png", (30, 30))
    red_signal_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "red_status.png"
    redSignalTk = tk.PhotoImage(file = red_signal_dir)
    redSig = graph_panel.create_image(833, 550, image = redSignalTk, anchor = 'c', state = NORMAL)

    #Arduino Status Label
    arduino_label = tk.Label(root, text = "Arduino Status", font = ("Helvetica", 16))
    arduino_label.place(relx = 0.9, rely = 0.77, anchor = 'c')

    # Arduino status text
    arduino_status = tk.Label(root, text = "Disconnected")
    arduino_status.place(relx = 0.9, rely = 0.81, anchor = 'c')

    # Arduino icon
    resize_Image("arduino_logo.png", "arduino_logo.png", (50, 33))
    arduino_logo_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "arduino_logo.png"
    arduinoIconTk = tk.PhotoImage(file = arduino_logo_dir)
    arduino_icon = graph_panel.create_image(725, 550, image = arduinoIconTk, anchor = 'c', state = NORMAL)

    # Server status label
    server_status = tk.Label(root, text = "Server Status", font = ("Helvetica", 16))
    server_status.place(relx = 0.70, rely = 0.77, anchor = 'c')
    #Server status dormant or running label
    status_bar = tk.Label(root, text = "Dormant")
    status_bar.place(relx = 0.70, rely = 0.81, anchor = 'c')
    # "Latest Data" label
    latest_data = tk.Label(root, text = "Latest Data", justify = CENTER, font = ("Helvetica", 16))
    latest_data.place(relx = 0.90, rely = 0.13, anchor='c')
    # X column label
    time_label = tk.Label(root, text = "Time")
    time_label.place(relx = .86, rely = 0.18, anchor = 'c')
    # Y column label
    data_label = tk.Label(root, text = "EMG Value (V)")
    data_label.place(relx = .95, rely = 0.18, anchor = 'c')
    # The following is a series of hard-locked labels that show the last 7 data points that came in
    data1key = tk.Label(root, text = "")
    data1key.place(relx = 0.86, rely = 0.23, anchor='c')
    data1value = tk.Label(root, text = "")
    data1value.place(relx = 0.94, rely = 0.23, anchor='c')

    data2key = tk.Label(root, text = "")
    data2key.place(relx = 0.86, rely = 0.31, anchor='c')
    data2value = tk.Label(root, text = "")
    data2value.place(relx = 0.94, rely = 0.31, anchor='c')

    data3key = tk.Label(root, text = "")
    data3key.place(relx = 0.86, rely = 0.39, anchor='c')
    data3value = tk.Label(root, text = "")
    data3value.place(relx = 0.94, rely = 0.39, anchor='c')

    data4key = tk.Label(root, text = "")
    data4key.place(relx = 0.86, rely = 0.47, anchor='c')
    data4value = tk.Label(root, text = "")
    data4value.place(relx = 0.94, rely = 0.47, anchor='c')

    data5key = tk.Label(root, text = "")
    data5key.place(relx = 0.86, rely = 0.55, anchor='c')
    data5value = tk.Label(root, text = "")
    data5value.place(relx = 0.94, rely = 0.55, anchor='c')

    data6key = tk.Label(root, text = "")
    data6key.place(relx = 0.86, rely = 0.63, anchor='c')
    data6value = tk.Label(root, text = "")
    data6value.place(relx = 0.94, rely = 0.63, anchor='c')

    # Button to start the server, has an icon on it
    resize_Image("start_server.png", "start_server.png", (20, 20))
    start_server_img_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "start_server.png"
    start_server = tk.PhotoImage(file = start_server_img_dir)
    start_btn = tk.Button(root, text = "    Start Server", image = start_server, compound = LEFT, command = lambda: acceptInput(start_btn, stop_btn, exit_btn, send_btn, clear_btn, data_btn, status_bar, config_btn))
    start_btn.place(relx = 0.3, rely = 0.79, relwidth = 0.2, relheight = 0.08, anchor = 'c')
    # Button to stop accepting data, has an icon on it
    resize_Image("stop_server.png", "stop_server.png", (20, 20))
    stop_server_img_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "stop_server.png"
    stop_server = tk.PhotoImage(file = stop_server_img_dir)
    stop_btn = tk.Button(root, text = "    Stop Server", image = stop_server, compound = LEFT, state = DISABLED, command = lambda: closeInput(start_btn, stop_btn, exit_btn, send_btn, clear_btn, data_btn, status_bar, config_btn))
    stop_btn.place(relx = 0.5, rely = 0.79, relwidth = 0.2, relheight = 0.08, anchor = 'c')

    # Button to exit the application
    exit_btn = tk.Button(root, text = "Exit Application", command = root.quit)
    exit_btn.place(relx = 0.92, rely = 0.05, anchor = 'c')
    # Button to elect to send the data to firebase
    resize_Image("firebase_logo.png", "firebase_logo.png", (24, 40))
    firebase_img_dir = os.path.dirname(os.path.realpath(__file__)) + "\\" + "firebase_logo.png"
    firebase_logo = tk.PhotoImage(file = firebase_img_dir)
    send_btn = tk.Button(root, text = "     Send to Firebase", image = firebase_logo, compound = LEFT, state = DISABLED, command = lambda: sendData(send_btn, clear_btn))
    send_btn.place(relx = 0.4, rely = 0.88, relwidth = 0.2, anchor = 'c')

    # Button to clear the data on the graph and in the table
    clear_btn = tk.Button(root, text = "Clear All Data", state = DISABLED, command = lambda: clearData(clear_btn))
    clear_btn.place(relx = 0.1, rely = 0.81, relwidth = 0.15, anchor = 'c')

    # Button to open previous data
    data_btn = tk.Button(root, text = "Open Past Data", command = lambda: openData(clear_btn))
    data_btn.place(relx = 0.1, rely = 0.76, relwidth = 0.15, anchor = 'c')

    # Button to open configuration window
    config_btn = tk.Button(root, text = "Open Config Window", command = lambda: openConfig(config_btn))
    config_btn.place(relx = 0.1, rely = 0.91, relwidth = 0.15, anchor = 'c')

    # Button to open Arduino connection window
    conn_btn = tk.Button(root, text = "Connect to Arduino", command = lambda: ArduinoConnect())
    conn_btn.place(relx = 0.1, rely = 0.86, relwidth = 0.15, anchor = 'c')

    #Start calling functions: these functions call themselves every 500 ms
    createGraph()
    updateGraph()
    updateTable()
    updateArduinoStatus()

    # start the mainloop
    root.mainloop()

# pass function to disable the normal Windows "X" button  
def disable_event():
    pass

# function for resizing an image
def resize_Image(imagePath, newFilename, newsize):
    filePath = os.path.dirname(os.path.realpath(__file__)) + "\\" + imagePath
    im1 = Image.open(filePath).resize((newsize[0], newsize[1]))
    filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), newFilename)
    im1.save(filename, 'png')

# function that runs in the separate thread that runs the server
def runFlask():
    global initialTime, ip_address
    #Start the initialTime
    initialTime = time.time()
    #Find the ip address of the local machine
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    #Create the Flask app
    app = Flask(__name__)
    @app.route("/")
    # Defining the home function which repeats every time a request is received
    def home():
        global x
        global y
        global firebase_data, stdev_thresh, stdevData, recvX, recvY, stdevlookbackpoints, stdevlookbacktime
        global accepting
        #Get the arguments
        args = request.args
        voltage = EMGToVoltage(int(args['EMG_value']))
        recvX.append(time.time() - initialTime)
        recvY.append(voltage)
        # If data is supposed to be recorded
        if accepting:
            
            # Add the timestamp to the x list
            x.append(time.time() - initialTime)
            # Add the EMG value to the y list
            y.append(voltage)
            
            

            if len(pastPoints) > stdevlookbackpoints:
                pastPoints.pop(0)
            pastPoints.append(voltage)
            try:
                stdevData.append(statistics.stdev(pastPoints))
            except:
                stdevData.append(0)
            # Set the timestamp key equal to the EMG value
            firebase_data[removePeriods(str(time.time() - initialTime))] = str(voltage) + ";;;" + str(stdevData[len(stdevData)-1])
            # Further data analysis for alarm detection will go here
            try:
                if statistics.stdev(pastPoints) > stdev_thresh and time.time() - initialTime > 100:
                    playsound(os.path.dirname(os.path.realpath(__file__)) + "\\" + "Alarm_Buzzer.wav")
            except:
                pass
        return "success"

    # Run the app
    app.run(debug = False, host = ip_address, port = 5000)

# updates the data table on the right side; calls itself every 750 ms
def updateTable():
    # Global variables to be used
    global x, y, accepting
    global data1key, data1value, data2key, data2value, data3key, data3value, data4key, data4value, data5key, data5value, data6key, data6value
    # If the Arduino is currently accepting and there is data in the data tables
    if accepting and len(x) > 0:
        # List to hold strings of hours
        hour_strings = []
        # updating labels 
        # Iterate through timestamps (in seconds)
        for time in x:
            # Convert to nicely formatted string of hours, minutes and seconds
            total_seconds = int(time)
            hours = int(total_seconds / 3600)
            mins = int(total_seconds / 60)
            seconds = total_seconds
            if total_seconds >= 60:
                seconds = total_seconds % 60

            seconds = str(seconds)
            if len(seconds) < 2:
                seconds = "0" + seconds
            mins = str(mins)
            if len(mins) < 2:
                mins = "0" + mins
            hours = str(hours)
            if len(hours) < 2:
                hours = "0" + hours

            hour_string = hours + ":" + mins + ":" + seconds
            hour_strings.append(hour_string)

        # Set all 6 data labels to those hour strings and the corresponding EMG value
        if len(x) >= 1:
            data1key['text'] = str(hour_strings[len(hour_strings)-1])
            data1value['text'] = str(y[len(y)-1])
        if len(x) >= 2:
            data2key['text'] = str(hour_strings[len(hour_strings)-2])
            data2value['text'] = str(y[len(y)-2])
        if len(x) >= 3:
            data3key['text'] = str(hour_strings[len(hour_strings)-3])
            data3value['text'] = str(y[len(y)-3])
        if len(x) >= 4:
            data4key['text'] = str(hour_strings[len(hour_strings)-4])
            data4value['text'] = str(y[len(y)-4])
        if len(x) >= 5:
            data5key['text'] = str(hour_strings[len(hour_strings)-5])
            data5value['text'] = str(y[len(y)-5])
        if len(x) >= 6:
            data6key['text'] = str(hour_strings[len(hour_strings)-6])
            data6value['text'] = str(y[len(y)-6])
    # After 500 ms, call self
    root.after(500, updateTable)

# Creates the initial blank graph
def createGraph():
    # globals
    global first, fig, ax, canvas, line, graph_frame, toolbar, stdevLine, thresh_line
    # Creating a special kind of figure
    fig = matplotlib.figure.Figure()
    # Adding a subplot
    ax = fig.add_subplot(1,1,1)
    # Title
    ax.set_title("AsthmAlarm Sensor Signal (V) vs Time (s)")
    # Y axis label
    ax.set_ylabel("EMG Value (V)")
    # X axis label
    ax.set_xlabel("Time Since Start (s)")
    # Set y bounds to 0-1100
    ax.set_ylim([0, 3.35])
    ax.set_xlim([0, 60])
    # Create a matplotlib / tkinter canvas object
    canvas = FigureCanvasTkAgg(fig, master=root)
    # Render the canvas
    canvas.draw()
    # place on tkinter gui
    canvas._tkcanvas.place(relx = 0.02, rely = 0.03, relwidth = 0.8, relheight = 0.70)
    if not first:
        toolbar.destroy()
    toolbar = NavigationToolbar2Tk(canvas, root)
    toolbar.update()
    first = False
    # Plot the data
    line, = ax.plot(x, y, color = "red", label = "EMG Value (V)")
    stdevLine, = ax.plot(x, stdevData, color = "blue", label = str(stdevlookbacktime)+"-Point Running Standard Deviation")
    threshold = []
    for i in range(len(x)):
        threshold.append(stdev_thresh)
    thresh_line, = ax.plot(x, threshold, color = 'black', label = "Alarm Threshold", linestyle = "--")
    ax.legend(loc = "upper left")

# Updates the graph based on the data every 750 ms
def updateGraph():
    # Globals
    global first, fig, ax, canvas, line, stdevLine, accepting, stdevlookbacktime, thresh_line
    # If data is being recorded
    if accepting:
        # Plot any new values; if nothing has changed, the graph won't change
        line, = ax.plot(x, y, color= "red", label = "EMG Value (V)")
        stdevLine, = ax.plot(x, stdevData, color = "blue", label = str(stdevlookbacktime)+"-Point Running Standard Deviation")
        threshold = []
        for i in range(len(x)):
            threshold.append(stdev_thresh)
        thresh_line, = ax.plot(x, threshold, color = 'black', label = "Alarm Threshold", linestyle = "--")
        # Draw the plot
        try:
            last_number = int(x[len(x)-1])
        except:
            last_number = 60
        if last_number < 60:
            last_number = 60
        ax.set_xlim(last_number-60, last_number)

        ax.draw_artist(line)
        ax.draw_artist(stdevLine)
        
        # Render the canvas from before
        canvas.draw()
    # Call self every 500 ms
    root.after(500, updateGraph)

# Starts accepting input; calls the show Signal function and allows the flask server to collect data
def acceptInput(start_btn, stop_btn, exit_btn, send_btn, clear_btn, data_btn, status_bar, config_btn):
    # Globals
    global accepting, initialTime
    # Set start time of accepting input
    initialTime = time.time()
    # Flip the boolean which controls many other functions
    accepting = True
    # Start btn disabled, stop btn enabled, and exit, send to firebase, clear, and open past data buttons are disabled
    start_btn.config(state = DISABLED)
    stop_btn.config(state = NORMAL)
    exit_btn.config(state = DISABLED)
    send_btn.config(state = DISABLED)
    clear_btn.config(state = DISABLED)
    data_btn.config(state = DISABLED)
    config_btn.config(state = DISABLED)
    status_bar['text'] = "Running"
    createGraph()
    # Since we are starting a new session, data must be cleared
    clearData(clear_btn)
    # Once this happens, start the loop of the sending animation of the signal bars
    root.after(250, lambda: showSignal1())

# Stops accepting input; sets global accepting to False
def closeInput(start_btn, stop_btn, exit_btn, send_btn, clear_btn, data_btn, status_bar, config_btn):
    # Globals
    global accepting, x, y
    # Flip boolean which controls many other functions
    accepting = False
    # Start btn enabled, stop btn disabled, exit btn enabled, open past data btn enabled. If there is data that was collected, enable firebase and clear buttons too
    start_btn.config(state = NORMAL)
    stop_btn.config(state = DISABLED)
    exit_btn.config(state = NORMAL)
    data_btn.config(state = NORMAL)
    status_bar['text'] = "Dormant"
    config_btn.config(state = NORMAL)
    if len(x) > 0 and len(y) > 0:
        send_btn.config(state = NORMAL)
        clear_btn.config(state = NORMAL)

# Sends the firebase_data variable to a new folder in firebase
def sendData(send_btn, clear_btn):
    global firebase_data, x, y, firebaseref, stdevData, pastPoints, patient_email, datem
    # Create string to index the data in the database
    today = datetime.today()
    datem = str(today.replace(microsecond=0))
    global SaveAs
    SaveAs = tk.Toplevel(root)
    SaveAs.geometry("300x300")
    EntryLabel = tk.Label(SaveAs, text = "Enter the desired name of the data file: ")
    EntryLabel.place(relx = 0.5, rely = 0.35, anchor = 'c')
    filename = tk.StringVar()
    fileNameEntry = tk.Entry(SaveAs, textvariable = filename)
    fileNameEntry.place(relx = 0.5, rely = 0.5, relwidth = 0.75, anchor = 'c')
    submit_btn = tk.Button(SaveAs, text = "Save", command = lambda: Saveas())
    submit_btn.place(relx = 0.5, rely = 0.65, anchor = 'c')
    def Saveas():
        global SaveAs, x, y, firebase_data, firebaseref, patient_email, stdevData, pastPoints, stdevlookbacktime, stdev_thresh, sendrate, datem
        #Writing to firebase
        
        final_filename = ""
        if filename.get() != "":
            final_filename = filename.get()
        else:
            final_filename = datem
        if patient_email != "":
            firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Sessions").child(removePeriods(final_filename)).child("Data").set(firebase_data)
            firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Sessions").child(removePeriods(final_filename)).update({
                "DateTime": datem,
                "ContainsSTDEV": "True",
                "Configuration": {
                    "Threshold": stdev_thresh,
                    "LookBackTime": stdevlookbacktime,
                    "SendRate": sendrate
                }
            })
            #Clearing data structures
            x = []
            y = []
            firebase_data = {}
            stdevData = []
            pastPoints = []
            # Clear data
            clearData(clear_btn)
        else:
            inputWin = tk.Toplevel(root)
            inputWin.geometry("200x200")
            inputWin.resizable(0, 0)

            entryvalue = tk.StringVar()
            entry = tk.Entry(inputWin, textvariable = entryvalue)
            entry.place(relx = 0.5, rely = 0.25, anchor = CENTER)

            label = tk.Label(inputWin, text = "Enter your patient account \nemail address here", font = ("Helvetica", 10))
            label.place(relx = 0.5, rely = 0.45, anchor = CENTER)

            errortext = tk.Label(inputWin, text = "", font = ("Helvetica", 8), fg="red")
            errortext.place(relx = 0.5, rely = 0.9, anchor = CENTER)

            save_btn = tk.Button(inputWin, text = "Save", command = lambda: newPatientEmail(entryvalue.get()))
            save_btn.place(relx = 0.5, rely = 0.8, anchor = CENTER)

            def newPatientEmail(input):
                global patient_email, ConfigDict, firebase_data, stdev_thresh, stdevlookbackpoints, stdevlookbacktime, sendrate, firebaseref, datem
                global x, y, pastPoints, stdevData
                if input not in email_list:
                    errortext['text'] = "Patient Account does not exist. Try again"
                    return
                if re.search(".+@.+\..+", input) == None:
                    errortext['text'] = "Email Address is not valid. Try again"
                    return
                patient_email = input
                ConfigDict['PatientAccount'] = patient_email
                firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Sessions").child(removePeriods(final_filename)).set({
                    "DateTime": datem,
                    "ContainsSTDEV": "True",
                    "Configuration": {
                        "Threshold": stdev_thresh,
                        "LookBackTime": stdevlookbacktime,
                        "SendRate": sendrate
                    }
                })
                firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Sessions").child(removePeriods(final_filename)).child("Data").set(firebase_data)
                inputWin.destroy()
                #Clearing data structures
                x = []
                y = []
                firebase_data = {}
                stdevData = []
                pastPoints = []
                # Clear data
                clearData(clear_btn)
                
        savedir = os.path.dirname(os.path.realpath(__file__)) + "\\AsthmAlarm_Data\\" + removePeriods(final_filename.replace(":", "-")) + ".txt"

        with open(savedir, "a+") as texthandle:
            texthandle.write("DateTime " + datem + "\n")
            texthandle.write("Configuration: " + str(stdevlookbacktime) + "\n")
            i = 0
            for i in list(range(len(x))):
                texthandle.write(str(x[i]) + "-->" + str(y[i]) + "-->" + str(stdevData[i]) + "\n")
                i += 1
        texthandle.close()
        SaveAs.destroy()
        # Now disable the send button
        send_btn.config(state = DISABLED)
    
# Clears the data on the graph and the data table; essentially deletes x and y and firebase_data
def clearData(clear_btn):
    # Globals
    global data1key, data1value, data2key, data2value, data3key, data3value, data4key, data4value, data5key, data5value, data6key, data6value
    global x, y, firebase_data, pastPoints, stdevData
    # Clear the data labels on the right hand side
    data1key['text'] = ""
    data1value['text'] = ""
    data2key['text'] = ""
    data2value['text'] = ""
    data3key['text'] = ""
    data3value['text'] = ""
    data4key['text'] = ""
    data4value['text'] = ""
    data5key['text'] = ""
    data5value['text'] = ""
    data6key['text'] = ""
    data6value['text'] = ""
    # Clear data structures
    x = []
    y = []
    firebase_data = {}
    pastPoints = []
    stdevData = []
    # Create blank graph
    createGraph()
    # Clear button disabled
    clear_btn.config(state = DISABLED)

#Hides the green signal image
def hideSignal():
    # Hides all four of the signal bars
    graph_panel.itemconfigure(signal1, state = "hidden")
    graph_panel.itemconfigure(signal2, state = "hidden")
    graph_panel.itemconfigure(signal3, state = "hidden")
    graph_panel.itemconfigure(signal4, state = "hidden")

# Shows the first signal bar
def showSignal1():
    # Shows the first one, hides the other three
    graph_panel.itemconfigure(signal1, state = NORMAL)
    graph_panel.itemconfigure(signal2, state = HIDDEN)
    graph_panel.itemconfigure(signal3, state = HIDDEN)
    graph_panel.itemconfigure(signal4, state = HIDDEN)
    # Calls the next show function in 250 ms
    root.after(250, showSignal2)

# Shows the second signal bar
def showSignal2():
    # Shows the second signal bar
    graph_panel.itemconfigure(signal2, state = NORMAL)
    # Calls the next show function in 250 ms
    root.after(250, showSignal3)

# Shows the third signal bar
def showSignal3():
    # Shows the third signal bar
    graph_panel.itemconfigure(signal3, state = NORMAL)
    # Calls the next show function in 250 ms
    root.after(250, showSignal4)

# Shows the fourth signal bar
def showSignal4():
    # Shows the last signal bar
    graph_panel.itemconfigure(signal4, state = NORMAL)
    # If the data is still being recorded, call the first show function again
    if accepting:
        root.after(250, showSignal1)
    # If data recording has stopped, hide all the signals and stop calling the other show functions
    else:
        graph_panel.itemconfigure(signal1, state = HIDDEN)
        graph_panel.itemconfigure(signal2, state = HIDDEN)
        graph_panel.itemconfigure(signal3, state = HIDDEN)
        graph_panel.itemconfigure(signal4, state = HIDDEN)

# Creates the window that allows the user to select data to view
def openData(clear_btn):
    global toolbar, stdevlookback, stdev_thresh
    # While loop is an error checking mechanism
    loop = True
    while loop:
        # Create file dialog box for .txt files
        filename = filedialog.askopenfilename(initialdir = os.path.dirname(os.path.realpath(__file__)), title = "Select a File to Open", filetypes = (("Text files", "*.txt"),))
        # Open the selected file
        if filename != "":
            try:
                with open(filename, "r") as texthandle:
                    # Initialize temporary data structures
                    past_x = []
                    past_y = []
                    pastStdData = []
                    struct = {}
                    title = ""
                    lookback = ""
                    # Iterate through lines
                    for line in texthandle:
                        # If it's a data line
                        if not line.startswith("DateTime") and not line.startswith("\n") and not line.startswith("Configuration"):
                            # Append the timestamp and the EMG value, which are split by "-->"
                            past_x.append(float(addPeriods(line.split("-->")[0])))
                            past_y.append(float(line.split("-->")[1]))
                            pastStdData.append(float(line.split("-->")[2].rstrip()))
                            # Struct population
                            struct[float(addPeriods(line.split("-->")[0]))] = float(line.split("-->")[1])
                        # If it's the title line, extract the date and time for showing later
                        elif line.startswith("DateTime"):
                            title = line.replace("DateTime ", "")
                            title = title.rstrip()
                        else:
                            lookback = int(line.split(": ")[1])
                    # Create figure
                    fig = matplotlib.figure.Figure()
                    # add subplot
                    ax = fig.add_subplot(1,1,1)
                    # Axis and main graph titles
                    ax.set_title("AsthmAlarm Sensor Signal (V) vs Time (s): " + title)
                    ax.set_xlabel("Time Since Start (s)")
                    ax.set_ylabel("AsthmAlarm Sensor Signal (V)")
                    # Y range
                    ax.set_ylim([0, 3.35])
                    
                    ax.set_xlim([0, 60])
                    
                    # new canvas
                    canvas = FigureCanvasTkAgg(fig, master=root)
                    # draw canvas
                    canvas.draw()
                    # place on tkinter
                    toolbar.destroy()
                    toolbar = NavigationToolbar2Tk(canvas, root)
                    toolbar.update()
                    canvas._tkcanvas.place(relx = 0.02, rely = 0.03, relwidth = 0.8, relheight = 0.70)
                    

                    # Plot the line
                    line, = ax.plot(past_x, past_y, color = "red", label = "EMG Value (V)")
                    line2, = ax.plot(past_x, pastStdData, color = 'blue', label = str(lookback)+"-Point Running Standard Deviation")
                    threshold = []
                    for i in range(len(past_x)):
                        threshold.append(stdev_thresh)
                    line3, = ax.plot(past_x, threshold, color = 'black', label = "Alarm Threshold")
                    ax.legend()
                # Clear button now available
                clear_btn.config(state = NORMAL)
                loop = False
            except:
            # if file contents are not compatible, show warning
                messagebox.showerror("File Open Warning", "File does not match the required data format. Please select an AsthmAlarm data formatted file")
                loop = True
        else:
            loop = False

#Updates the Arduino Status area of the GUI to match the status of HTTP requests coming in
def updateArduinoStatus():
    global arduino_label, arduino_icon, arduino_conn
    try:
        # If the arduino has not transmitted in a while
        if time.time() - initialTime - recvX[len(recvX) - 1] > 8:
            # Show the red dot
            graph_panel.itemconfigure(greenSig, state = HIDDEN)
            graph_panel.itemconfigure(redSig, state = NORMAL)
            # Set label text to disconnected
            arduino_status['text'] = "Disconnected"
            # Set boolean
            arduino_conn = False
        else:
            # Show the green dot
            graph_panel.itemconfigure(greenSig, state = NORMAL)
            graph_panel.itemconfigure(redSig, state = HIDDEN)
            # Set label text to connected
            arduino_status['text'] = "Connected"
            # set boolean
            arduino_conn = True
    except:
        pass
    root.after(500, updateArduinoStatus)

# Recursive algorithm to connect to Arduino and communicate with it
def ArduinoConnect():
    global recvX, recvY, arduino_conn, serial_port, networks, sendrate, ConfigDict
    if not arduino_conn:
        connWindow = tk.Toplevel(root)
        connWindow.geometry("300x300")
        connWindow.resizable(False, False)

        selectLabel = tk.Label(connWindow, text = "Select a Preloaded Wifi network")
        selectLabel.place(relx = 0.5, rely = 0.07, anchor = CENTER)

        submit1 = tk.Button(connWindow, text = "Submit Preloaded Wifi", command = lambda: connArduino(selected.get(), networks[selected.get()], False))
        submit1.place(relx = 0.5, rely = 0.35, anchor = CENTER)

        newLabel = tk.Label(connWindow, text = "Enter Wifi Name and Password for New Network")
        newLabel.place(relx = 0.5, rely = 0.6, anchor = CENTER)

        tk.Label(connWindow, text = "Network SSID: ").place(relx = 0.45, rely = 0.7, anchor = E)
        tk.Label(connWindow, text = "Network password: ").place(relx = 0.45, rely = 0.8, anchor = E)

        newBtn = tk.Button(connWindow, text = "Submit New Network Info", command = lambda: connArduino(name.get(), password.get(), True))
        newBtn.place(relx = 0.5, rely = 0.9, anchor = CENTER)

        options = []
        for network in networks:
            options.append(network)
        
        selected = tk.StringVar()
        drop_menu = tk.OptionMenu(connWindow, selected, *options)
        drop_menu.place(relx = 0.5, rely = 0.17, anchor = CENTER)

        name = tk.StringVar()
        password = tk.StringVar()
        nameEntry = tk.Entry(connWindow, textvariable = name)
        nameEntry.place(relx = 0.7, rely = 0.7, anchor = CENTER)

        passEntry = tk.Entry(connWindow, textvariable = password)
        passEntry.place(relx = 0.7, rely = 0.8, anchor = CENTER)


        def connArduino(network, password, new):
            global serial_port, ConfigDict, sendrate, networks, arduino_conn
            statusWin = tk.Toplevel()
            statusWin.geometry("300x200")
            statusWin.resizable(False, False)
            # show status as trying to connect to the Arduino
            # Cycle through COM ports until you find one
            # If cycling for more than 10 seconds, prompt user to check the USB connection in the windows device manager and make sure that the Arduino is connected
            tk.Label(statusWin, text = "Plug AsthmAlarm into a USB port on your computer").place(relx = 0.5, rely = .1, anchor = CENTER)
            status = tk.Label(statusWin, text = "Searching for Arduino on COM ports ... \nDon't try to interact with this window")
            status.place(relx = 0.5, rely = .25, anchor = CENTER)
            warnStatus = tk.Label(statusWin, text = "")
            warnStatus.place(relx = 0.5, rely = 0.4, anchor = CENTER)
            statusWin.update()
            connWindow.update()
            serial_port = "COM257"
            global COMfound
            COMfound = False
            def searchCOM():
                global arduino_conn, serial_port, ip_address, COMfound
                COMfound = False
                start_time = time.time()
                while not COMfound and time.time() - start_time < 15:
                    for i in range(256):
                        port = "COM" + str(i)
                        print(port)
                        try:
                            serial_port = serial.Serial(port, 9600, timeout = 1)
                            
                        # Copy-pasta for home network - Esben
                        # ;SSID:Fios-IZZOQ,jar9882pin4025wire][192.168.1.176;
                            print(serial_port.portstr)
                            COMfound = True
                            status['text'] = "COM port found\nWaiting for Arduino to signal that it \nis ready to receive information"
                            statusWin.update()
                            time.sleep(1)
                            break
                        except:
                            pass
                        time.sleep(0.01)
                        statusWin.update()
                        connWindow.update()
                        root.update()
            searchCOM()
            
            if COMfound:
                print("Starting waiting for Serial")
                nextChar = serial_port.readline() 
                print("First Line: " + str(nextChar))  
                # Waiting for indication that Arduino is ready to receive
                
                while not str(nextChar).__contains__("Waiting for input"):
                    nextChar = serial_port.readline()
                    print(str(nextChar))
                    statusWin.update()
                    connWindow.update()
                    root.update()
                status['text'] = "Sending wifi information"
                serial_port.write(str.encode("PYTHON CONN"))
                print(";SSID:" + network + "," + password + "][" + str(ip_address) + "<>" + str(sendrate) + ";") # ;SSID:Fios-IZZOQ,jar9882pin4025wire][192.168.1.212<>1500;
                serial_port.write(str.encode(";SSID:" + network + "," + password + "][" + str(ip_address) + "<>" + str(sendrate) + ";"))
                # Copy-pasta for home network - Esben
                # ;SSID:Fios-IZZOQ,jar9882pin4025wire][192.168.1.176;
                time.sleep(3)
                status['text'] = "Arduino is attempting to connect"
                nextChar = serial_port.readline()
                while not str(nextChar).__contains__("ARD"):
                    nextChar = serial_port.readline()
                    print(str(nextChar))
                    statusWin.update()
                    connWindow.update()
                    root.update()
                if str(nextChar).__contains__("ARD-CONNECT"):
                    arduino_conn = True
                elif str(nextChar).__contains__("ARD-DISCONNECT"):
                    arduino_conn = False

            if not arduino_conn:
                status['text'] = "Arduino connection failed: Redirecting to wifi page ... "
                statusWin.update()
                time.sleep(2)
                statusWin.destroy()
                nameEntry.delete(0, END)
                passEntry.delete(0, END)
                selected.set("")
            else:
                status['text'] = "Arduino connected"
                statusWin.update()
                time.sleep(1.5)
                statusWin.destroy()
                connWindow.destroy()
                if new:
                    networks[network] = password
                    print(networks)

# Opens the configuration window which can customize report rate and wifi networks
def openConfig(config_btn):
    global drop_menu, ConfigDict, networks, sendrate, options
    configWin = tk.Toplevel()
    configWin.resizable(0,0)
    configWin.geometry("500x600")
    configWin.title("AsthmAlarm Configuration Window")
    tk.Label(configWin, text = "Manage Networks", font = ('Helvetica', 13)).place(relx = 0.5, rely = 0.03, anchor = CENTER)
    selected = tk.StringVar()
    options = []
    for network in networks:
        options.append(network)
    drop_menu = tk.OptionMenu(configWin, selected, *options)
    drop_menu.place(relx = 0.5, rely = 0.09, anchor = CENTER)

    error_label = tk.Label(configWin, text = "", fg = 'red')
    error_label.place(relx = 0.35, rely = 0.95, anchor = CENTER)

    def deleteNetwork():
        global drop_menu
        if selected.get() != "":
            networks.pop(selected.get())
            options.pop(options.index(selected.get()))
            selected.set("")
            drop_menu.destroy()
            drop_menu = tk.OptionMenu(configWin, selected, *options)
            drop_menu.place(relx = 0.5, rely = 0.12, anchor = CENTER)
        else:
            pass

    def addNetwork():
        global ConfigDict
        newWin = tk.Toplevel()
        newWin.resizable(0,0)
        newWin.geometry("250x250")
        ssid = tk.StringVar()
        passcode = tk.StringVar()
        ssid_entry = tk.Entry(newWin, textvariable = ssid)
        ssid_entry.place(relx = 0.4, rely = 0.1, anchor = NW)
        ssid_label = tk.Label(newWin, text = "New SSID")
        ssid_label.place(relx = 0.4, rely = 0.1, anchor = NE)
        pass_entry = tk.Entry(newWin, textvariable = passcode)
        pass_entry.place(relx = 0.4, rely = 0.3, anchor = NW)
        pass_label = tk.Label(newWin, text = "New Password")
        pass_label.place(relx = 0.4, rely = 0.3, anchor = NE)
        def addToConfig():
            global ConfigDict, drop_menu, options
            networks[ssid.get()] = passcode.get()
            """ ConfigDict = {"Send_Rate": sendrate,
                "Wifi_Info": networks
            } """
            """ with open(os.path.dirname(os.path.realpath(__file__)) + "\\" + "config.json", "w") as outfile:
                json.dump(ConfigDict, outfile) """
            outfile.close()
            newWin.destroy()
            drop_menu.destroy()
            options = []
            for network in networks:
                options.append(network)
            drop_menu = tk.OptionMenu(configWin, selected, *options)
            drop_menu.place(relx = 0.5, rely = 0.12, anchor = CENTER)
        submit_btn = tk.Button(newWin, text = "Create New Network", command = lambda: addToConfig())
        submit_btn.place(relx = 0.5, rely = 0.5, anchor = CENTER)

    def saveChanges():
        global sendrate, stdev_thresh, stdevlookbacktime, patient_email, ConfigDict, email_list
        
        if newrate.get() < 100 or newrate.get() > 5000:
            error_label['text'] = "Send Rate is out of bounds"
            return None
        
        try:
            newThreshold = float(newThresh.get())
        except:
            error_label['text'] = "New Threshold must be a decimal number"
            return None
        
        if 0 > newLookBack.get() or newLookBack.get() > 1800:
            error_label['text'] = "New Look Back time is out of bounds"
            return None
            
        if re.search(".*@.*\..*", email.get()) == None:
            error_label['text'] = "New Patient email is not an email"
            return None
            
        if 0 > float(newThresh.get())  or float(newThresh.get()) > 3.3:
            error_label['text'] = "New Threshold must be between 0 and 3.3"
            return None

        if email.get().strip() not in email_list:
            error_label['text'] = "New Patient email is not registered yet"
            return None
        
        try:
            if newrate.get() >= 500 and newrate.get() <= 5000 and float(newThresh.get()) > 0 and float(newThresh.get()) < 3.3 and newLookBack.get() > 0 and newLookBack.get() < 1800 and re.search(".*@.*\..*", email.get()) != None and email.get().strip() in email_list:
                sendrate = newrate.get()
                stdev_thresh = float(newThresh.get())
                stdevlookbacktime = newLookBack.get()
                patient_email = email.get()
                configWin.destroy()
                config_btn.config(state = NORMAL)
            else:
                pass
        except:
            pass
        
    delete_btn = tk.Button(configWin, text = "Delete network", command = lambda: deleteNetwork())
    delete_btn.place(relx = 0.35, rely = 0.15, anchor = CENTER)

    add_btn = tk.Button(configWin, text = "Add a network", command = lambda: addNetwork())
    add_btn.place(relx = 0.65, rely = 0.15, anchor = CENTER)

    email = tk.StringVar()
    email.set(patient_email)
    tk.Label(configWin, text = "Change AsthmAlarm Patient Account", font = ('Helvetica', 13)).place(relx = 0.5, rely = 0.23, anchor = CENTER)
    emailEntry = tk.Entry(configWin, textvariable = email)
    emailEntry.place(relx = 0.5, rely = 0.28, anchor = CENTER, relwidth = 0.5)

    tk.Label(configWin, text = "Customize Arduino Report Rate", font = ('Helvetica', 13)).place(relx = 0.5, rely = 0.35, anchor = CENTER)
    tk.Label(configWin, text = '''Sets how many milliseconds are between each Arduino EMG report.\n Default is 1000, range is 500 - 5000''', font = ('Helvetica', 8)).place(relx = 0.5, rely = 0.40, 
        anchor = CENTER)
    newrate = tk.IntVar()
    newrate.set(sendrate)
    rateEntry = tk.Entry(configWin, textvariable = newrate)
    rateEntry.place(relx = 0.5, rely = 0.45, anchor = CENTER)

    tk.Label(configWin, text = "Adjust Alarm Threshold", font = ("Helvetica", 12)).place(relx = 0.5, rely = 0.52, anchor = CENTER)
    tk.Label(configWin, text = "Sets the level of running standard deviation that must be achieved for the alarm to go off. \nThe higher this value, the less sensitive the alarm will be, and vice versa. \nMust be an positive integer", 
        font = ("Helvetica", 8)).place(relx = 0.5, rely = 0.58, anchor = CENTER)

    newThresh = tk.StringVar()
    newThresh.set(str(stdev_thresh))
    threshEntry = tk.Entry(configWin, textvariable = newThresh)
    threshEntry.place(relx = 0.5, rely = 0.67, anchor = CENTER)

    tk.Label(configWin, text = "Adjust Alarm Look-Back Distance", font = ("Helvetica", 12)).place(relx = 0.5, rely = 0.77, anchor = CENTER)
    tk.Label(configWin, text = "Sets the number of seconds of data taken into consideration when calculating \nrunning standard deviation. Must be a positive integer", font = ("Helvetica", 8)).place(relx = 0.5, rely = 0.82, anchor = CENTER)

    newLookBack = tk.IntVar()
    newLookBack.set(stdevlookbacktime)
    lookBackEntry = tk.Entry(configWin, textvariable = newLookBack)
    lookBackEntry.place(relx = 0.5, rely = 0.88, anchor = CENTER)

    save_changes = tk.Button(configWin, text = "Save", command = lambda: saveChanges())
    save_changes.place(relx = 0.85, rely = 0.95, anchor = CENTER)

# Converts EMG value to a voltage value
def EMGToVoltage(inputEMG):
    inputVolt = round((3.3 * inputEMG / 1023), 5)
    return inputVolt

if __name__ == "__main__":
    main()
    # Saving any changed information to the config.json file
    ConfigDict = {
        "Send_Rate": sendrate, 
        "Wifi_Info": networks,
        "Stdev_Thresh": stdev_thresh,
        "StDevLookBack": stdevlookbacktime,
        "PatientAccount": patient_email
    }
    if patient_email != "":
        firebaseref.database().child("Patients").child(removePeriods(patient_email)).child("Configuration").set({
            "Send_Rate": sendrate,
            "Stdev_Thresh": stdev_thresh,
            "StDevLookBack": stdevlookbacktime
        })
    with open(os.path.dirname(os.path.realpath(__file__)) + "\\" + "config.json", "w") as outfile:
        json.dump(ConfigDict, outfile)
    # input()