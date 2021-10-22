"""
Project Name: WS2021_5 ; AsthmAlarm
Team Members: Emily Luo, Matthew Shen, Esben Nielsen, Pranavi Gollamudi
Date: 6/03/2021
Task Description: Serves as a test platform for changing the range of data before we switched to a range of 0-3.3
"""

import statistics
from tkinter import filedialog
import os
import matplotlib.pyplot as plt
from datetime import datetime
filename = filedialog.askopenfilename(initialdir = os.path.dirname(os.path.realpath(__file__)), title = "Select a File to Open", filetypes = (("Text files", "*.txt"),))

with open(filename, "r") as texthandle:
    # Initialize temporary data structures
    past_x = []
    past_y = []
    stdevList = []
    struct = {}
    title = ""
    # Iterate through lines
    for line in texthandle:
        # If it's a data line
        if not line.startswith("DateTime") and not line.startswith("\n"):
            # Append the timestamp and the EMG value, which are split by "-->"
            past_x.append(int(line.split("-->")[0]))
            past_y.append(int(line.split("-->")[1]))
            stdevList.append(float(line.split("-->")[2]))
            # Struct population
            struct[int(line.split("-->")[0])] = int(line.split("-->")[1])
        # If it's the title line, extract the date and time for showing later
        elif line.startswith("DateTime"):
            title = line.replace("DateTime ", "")
            title = title.rstrip()
newY = []
for i in past_y:
    newY.append(float(i / (1023 / 3.3)))

today = datetime.today()
datem = str(today.replace(microsecond=0))
#Writing to firebase
# firebaseref.database().child(datem).set(firebase_data)
#Writing to a new data file
savedir = os.path.dirname(os.path.realpath(__file__)) + "\\AsthmAlarm_Data\\AsthmAlarm" + datem.replace(":", "-") + "NEW.txt"
with open(filename, "a+") as texthandle:
    texthandle.write("DateTime " + datem + "\n")
    i = 0
    for data_point in past_x:
        texthandle.write(str(data_point) + "-->" + str(newY[i]) + "-->" + str(stdevList[i]) + "\n")
        i += 1
texthandle.close()