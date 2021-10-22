import pyrebase
import statistics
from datetime import datetime

def removePeriods(input):
    while input.__contains__("."):
        input = input.replace(".", "_()")
    return input

def addPeriods(input):
    while input.__contains__("_()"):
        input = input.replace("_()", ".")
    return input

config = {
    "apiKey": "AIzaSyCe9YmRHZIV3RdGZOzBUBsrP3EMjLPYKx4",
    "authDomain": "asthmalarm.firebaseapp.com",
    "databaseURL": "https://asthmalarm.firebaseio.com",
    "storageBucket": "asthmalarm.appspot.com"
    }
# Firebase reference app
firebaseref = pyrebase.initialize_app(config)

sessionDict = dict(firebaseref.database().child("Patients").child("magnuscarlsen@gmail_()com").child("Sessions").get().val())
counter = 0
for thing in sessionDict.keys():
    if thing != "Trial7 30N 60H":
        continue
    x = []
    y = []
    stdev = []
    pastPoints = []
    title = thing
    print(title)
    n = sessionDict[thing]['Configuration']['LookBackTime']
    sendrate = sessionDict[thing]['Configuration']['SendRate']
    thresh = sessionDict[thing]['Configuration']['Threshold']
    datem = sessionDict[thing]['DateTime']
    print("Look Back: ", n)
    sortpoints = []
    stdevPoints = []
    for i in sessionDict[thing]['Data'].keys():
        x.append(i)     #Periods removed format
        y.append(sessionDict[thing]['Data'][i])     #correct formal decimal format
        sortpoints.append({"x": float(addPeriods(i)), "y": sessionDict[thing]['Data'][i]})

        
        

        
            
    for i in range(len(sortpoints)):
        min = sortpoints[i]['x']
        minObj = sortpoints[i]
        minID = i
        for j in range(i, len(sortpoints)): 
            if sortpoints[j]['x'] < min:
                min = sortpoints[j]['x']
                minObj = sortpoints[j]
                minID = j
        temp = sortpoints[i]
        sortpoints[i] = minObj
        sortpoints[minID] = temp   

    for i in range(len(sortpoints)):
        if len(pastPoints) > n:
            pastPoints.pop(0)
        pastPoints.append(sortpoints[i]['y'])
        try:
            stdev.append(statistics.stdev(pastPoints))
            stdevPoints.append({"x": float(sortpoints[i]['x']), "y": statistics.stdev(pastPoints)})
        except:
            stdev.append(0)
            stdevPoints.append({"x": float(sortpoints[i]['x']), "y": 0})
    
    # for i in range(len(stdevPoints)):
    #     min = stdevPoints[i]['x']
    #     minObj = stdevPoints[i]
    #     minID = i
    #     for j in range(i, len(stdevPoints)): 
    #         if stdevPoints[j]['x'] < min:
    #             min = stdevPoints[j]['x']
    #             minObj = stdevPoints[j]
    #             minID = j
    #     temp = stdevPoints[i]
    #     stdevPoints[i] = minObj
    #     stdevPoints[minID] = temp 

    # print(sortpoints)
    # print(stdevPoints)
    # print(stdev)
    # print(pastPoints)
    newFirebase = {}
    for i in range(len(x)):
        newFirebase[removePeriods(str(sortpoints[i]['x']))] = str(sortpoints[i]['y']) + ";;;" + str(stdevPoints[i]['y'])
    for item in newFirebase.items():
        print(item)
    counter += 1
    firebaseref.database().child("Patients").child("magnuscarlsen@gmail_()com").child("Sessions").child(title).child("Data").update(newFirebase)
    firebaseref.database().child("Patients").child("magnuscarlsen@gmail_()com").child("Sessions").child(title).child("Configuration").update({
        "LookBackTime": n,
        "SendRate": sendrate,
        "Threshold": thresh
    })
    firebaseref.database().child("Patients").child("magnuscarlsen@gmail_()com").child("Sessions").child(title).update({
        "DateTime": datem,
        "ContainsSTDEV": 'True'
    })