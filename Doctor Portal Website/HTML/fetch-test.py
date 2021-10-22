from flask import Flask, jsonify
from flask import request
import socket

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

app = Flask(__name__)
@app.route("/", methods = ['GET'])
def home():
    args = request.args
    response = jsonify(message="Simple server is running")

    # Enable Access-Control-Allow-Origin
    response.headers.add("Access-Control-Allow-Origin", "*")
    print(args['Email'])
    return "success"

app.run(debug = False, port = 5000, host= ip_address)