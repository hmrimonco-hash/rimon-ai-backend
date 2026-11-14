import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]
RETRY_CODES = (429, 500, 502, 503, 504)

MODULES = {
    "study": "You are a patient study tutor for a university student. Explain clearly and concisely. Reply in the same language the user writes in (Bengali, Banglish or English).",
    "other": "You are a helpful personal assistant. Be brief and clear. Reply in the same language the user writes in (Bengali, Banglish or English).",
}
NOT_BUILT = ("planner", "research")


def gemini(text, system=None, file=None, timeout=10):
    parts = []
    if file:
        parts.append({"inline_data": {"mime_type": file["mime"], "data": file["data"]}})
    parts.append({"text": text})
    body = {"contents": [{"parts": parts}]}
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    headers = {
        "x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""),
        "Content-Type": "application/json",
    }
    last = "no model tried"
    for model in MODELS:
        try:
            resp = requests.post(
                f"{BASE}{model}:generateContent",
                headers=headers,
                json=body,
                timeout=timeout,
            )
        except requests.RequestException as e:
            last = f"{model}: {type(e).__name__}"
            continue
        if resp.status_code in RETRY_CODES:
            last = f"{model}: HTTP {resp.status_code}"
            continue
        resp.raise_for_status()
        parts = resp.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    raise RuntimeError("all models failed (" + last + ")")


def route(message):
    answer = gemini(
        message,
        system="Classify the user's message into exactly one word: study, planner, research, or other. "
        "study = learning or explaining a subject; planner = reminders, tasks, schedule; "
        "research = finding information about a topic; other = anything else. "
        "Reply with only that one word.",
    ).lower()
    for name in ("study", "planner", "research"):
        if name in answer:
            return name
    return "other"


@app.route("/")
def home():
    return jsonify(status="ok", message="Rimon AI backend is running")


ALLOWED = (
    "image/png", "image/jpeg", "image/webp", "image/heic", "image/heif",
    "application/pdf", "text/plain",
)


@app.route("/chat", methods=["GET", "POST"])
def chat():
    token = os.environ.get("APP_TOKEN")
    if not token or request.args.get("t") != token:
        return jsonify(error="not allowed"), 403
    file = None
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        message = (data.get("q") or "").strip()
        file = data.get("file")
        if file:
            if file.get("mime") not in ALLOWED or not file.get("data"):
                return jsonify(error="this file type is not supported"), 400
            if len(file["data"]) > 7_000_000:
                return jsonify(error="file is too large"), 400
            if not message:
                message = "Summarize this file."
    else:
        message = request.args.get("q", "")
    if not message:
        return jsonify(error="no question"), 400
    try:
        module = "study" if file else route(message)
        if module in NOT_BUILT:
            return jsonify(module=module, answer="This module is not built yet.")
        answer = gemini(message, MODULES[module], file, 25 if file else 10)
        return jsonify(module=module, answer=answer)
    except (requests.RequestException, KeyError, IndexError, RuntimeError) as e:
        return jsonify(error="gemini call failed", detail=str(e)[:200]), 502
