from flask import Flask, jsonify
from db import DBManager

app = Flask(__name__)

db_manager = DBManager("CONN STRING GET FROM ENV VARIABLE OR .ENV")


@app.route("/")
def hello_world():
    return jsonify({"message": "Hello, World!", "status": "success"})
