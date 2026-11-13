import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

MODEL = "gemini-3.1-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


@app.route("/")
def home():
    return jsonify(status="ok", message="Rimon AI backend is running")


@app.route("/ask")
def ask():
    token = os.environ.get("APP_TOKEN")
    if not token or request.args.get("t") != token:
        return jsonify(error="not allowed"), 403
    question = request.args.get("q", "")
    if not question:
        return jsonify(error="no question"), 400
    resp = requests.post(
        URL,
        headers={
            "x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""),
            "Content-Type": "application/json",
        },
        json={"contents": [{"parts": [{"text": question}]}]},
        timeout=30,
    )
    if resp.status_code != 200:
        return jsonify(error="gemini error", status=resp.status_code, detail=resp.text[:300]), 502
    try:
        parts = resp.json()["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        return jsonify(error="no answer returned"), 502
    return jsonify(answer="".join(p.get("text", "") for p in parts))
