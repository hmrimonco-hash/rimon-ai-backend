
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify(status="ok", message="Rimon AI backend is running")
