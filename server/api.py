import logging
from flask import Flask, jsonify
from db_manager import DBManager
from finance_manager import FinanceManager
from db_items import Holding, Transaction

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO  # change to DEBUG for db cache logging
)

DB_CONNECTION_STR = "CONNECTION STRING HERE FROM sys.env or .env file"
db_manager = DBManager(
    DB_CONNECTION_STR,
    flask_logger=app.logger,
    enable_cache=True
)

# constructor may need modification later
finance_manager = FinanceManager(flask_logger=app.logger)

# No logic should really be performed here with the exception of Error handling
# app.logger.[warning, error, info, debug] can be used for logging
# DBManager and FinanceManager should contain query logic
# this controller should be stupid and not know anything


@app.route("/")
def hello_world():
    return jsonify({"message": "Hello, World!", "status": "success"})
