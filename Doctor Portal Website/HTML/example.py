fulldict = dict()

fulldict[justHour] = {}
for i in range(len(gsrValues)):
    fulldict[justHour][justSeconds[i]] = {
        "Times": justSeconds[i],
        "GSR Sensor Value": gsrValues[i],
        "Skin Resistance (in ohms)": resistanceValues[i],
        "Are you dehydrated?": dehydratedValues[i]
    }

firebase.database().child("test3").child("Sessions").child(justDate).set(fulldict)