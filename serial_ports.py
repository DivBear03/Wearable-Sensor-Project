"""
Project Name: WS2021_5 ; AsthmAlarm
Team Members: Emily Luo, Matthew Shen, Esben Nielsen, Pranavi Gollamudi
Date: 6/03/2021
Task Description: Test platform for the pyserial library for wired communication between the AsthmAlarm application and the Arduino
"""

import serial
for i in range(256):
    try:
        ser = serial.Serial("COM"+str(i), 9800, timeout = 1)
        ser.write("Hello")
        print(ser.portstr)
    except:
        print("COM"+str(i)+" rejected")