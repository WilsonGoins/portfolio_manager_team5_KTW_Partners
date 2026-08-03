import os
import sys

# server/ modules import each other flat (`from db_manager import DBManager`),
# so the package dir has to be importable before the Flask app is pulled in.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from api import app  # noqa: E402,F401  Vercel serves this WSGI object
