import os
import time
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

RELAY_KEY = os.environ.get("RELAY_KEY", "")
PORT = int(os.environ.get("PORT", "10000"))

pending_commands = []
lock = threading.Lock()


def authorized():
    return (
        RELAY_KEY
        and request.headers.get("X-Relay-Key") == RELAY_KEY
    )


@app.get("/")
def home():
    return jsonify({
        "service": "Laptop Remote Relay",
        "status": "online"
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/command")
def add_command():
    if not authorized():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    command = str(data.get("command", "")).strip().lower()

    allowed = {
        "status",
        "screenshot",
        "lock",
        "sleep",
        "open_notepad",
        "open_calculator",
        "open_paint",
        "open_explorer",
    }

    if command not in allowed:
        return jsonify({"error": "Command not allowed"}), 400

    with lock:
        pending_commands.append({
            "id": str(time.time_ns()),
            "command": command,
        })

    return jsonify({"status": "queued", "command": command})


@app.get("/poll")
def poll():
    if not authorized():
        return jsonify({"error": "Unauthorized"}), 401

    with lock:
        commands = pending_commands[:]
        pending_commands.clear()

    return jsonify({"commands": commands})


@app.get("/status")
def status():
    if not authorized():
        return jsonify({"error": "Unauthorized"}), 401

    with lock:
        queue_size = len(pending_commands)

    return jsonify({
        "relay": "online",
        "queued_commands": queue_size
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
