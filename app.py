import os
import time
import threading
from flask import Flask, request, jsonify, render_template_string, session

app = Flask(__name__)

RELAY_KEY = os.environ.get("RELAY_KEY", "")
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "")
PORT = int(os.environ.get("PORT", "10000"))

# Used only for the panel login session.
app.secret_key = os.environ.get("PANEL_PASSWORD", "change-this-secret")

pending_commands = []
lock = threading.Lock()


# ---------- RELAY SECURITY ----------

def relay_authorized():
    return (
        RELAY_KEY
        and request.headers.get("X-Relay-Key") == RELAY_KEY
    )


# ---------- PHONE PANEL SECURITY ----------

def panel_logged_in():
    return session.get("panel_logged_in") is True


# ---------- PHONE PANEL ----------

PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Laptop Remote</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #111;
            color: white;
            text-align: center;
            padding: 20px;
            margin: 0;
        }

        .container {
            max-width: 500px;
            margin: auto;
        }

        h1 {
            margin-bottom: 8px;
        }

        .subtitle {
            color: #aaa;
            margin-bottom: 25px;
        }

        button {
            width: 100%;
            padding: 17px;
            margin: 7px 0;
            font-size: 18px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
        }

        .status {
            background: #222;
            padding: 15px;
            border-radius: 12px;
            margin-top: 20px;
            min-height: 25px;
        }

        .danger {
            margin-top: 25px;
        }

        .logout {
            background: #333;
            color: white;
        }
    </style>
</head>

<body>

<div class="container">

    <h1>💻 Laptop Remote</h1>
    <div class="subtitle">Remote control panel</div>

    <button onclick="sendCommand('status')">
        🟢 Status
    </button>

    <button onclick="sendCommand('lock')">
        🔒 Lock Laptop
    </button>

    <button onclick="sendCommand('sleep')">
        😴 Sleep Laptop
    </button>

    <button onclick="sendCommand('open_notepad')">
        📝 Notepad
    </button>

    <button onclick="sendCommand('open_calculator')">
        🧮 Calculator
    </button>

    <button onclick="sendCommand('open_paint')">
        🎨 Paint
    </button>

    <button onclick="sendCommand('open_explorer')">
        📁 Explorer
    </button>

    <div class="status" id="result">
        Ready...
    </div>

    <button class="logout" onclick="logout()">
        Logout
    </button>

</div>

<script>

async function sendCommand(command) {

    const result = document.getElementById("result");

    result.innerText = "⏳ Sending " + command + "...";

    try {

        const response = await fetch("/panel/command", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                command: command
            })
        });

        const data = await response.json();

        if (response.ok) {
            result.innerText =
                "✅ " + JSON.stringify(data);
        } else {
            result.innerText =
                "❌ " + JSON.stringify(data);
        }

    } catch (error) {

        result.innerText =
            "❌ Connection failed";

    }
}


async function logout() {

    await fetch("/logout", {
        method: "POST"
    });

    window.location.href = "/";
}

</script>

</body>
</html>
"""


LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>Laptop Remote Login</title>

    <style>

        body {
            font-family: Arial, sans-serif;
            background: #111;
            color: white;
            text-align: center;
            padding: 40px 20px;
        }

        .container {
            max-width: 400px;
            margin: auto;
        }

        input {
            width: 100%;
            box-sizing: border-box;
            padding: 16px;
            margin: 15px 0;
            border-radius: 10px;
            border: none;
            font-size: 16px;
        }

        button {
            width: 100%;
            padding: 16px;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            cursor: pointer;
        }

        .error {
            color: #ff7777;
            margin-top: 15px;
        }

    </style>

</head>

<body>

<div class="container">

    <h1>🔐 Laptop Remote</h1>

    <form method="POST" action="/login">

        <input
            type="password"
            name="password"
            placeholder="Panel password"
            required
        >

        <button type="submit">
            Login
        </button>

    </form>

    {% if error %}
        <div class="error">
            ❌ Incorrect password
        </div>
    {% endif %}

</div>

</body>
</html>
"""


# ---------- ROUTES ----------

@app.get("/")
def home():

    if panel_logged_in():
        return render_template_string(PANEL_HTML)

    return render_template_string(
        LOGIN_HTML,
        error=False
    )


@app.post("/login")
def login():

    password = request.form.get("password", "")

    if PANEL_PASSWORD and password == PANEL_PASSWORD:

        session["panel_logged_in"] = True

        return render_template_string(PANEL_HTML)

    return render_template_string(
        LOGIN_HTML,
        error=True
    ), 401


@app.post("/logout")
def logout():

    session.clear()

    return jsonify({
        "status": "logged out"
    })


# ---------- PHONE → RELAY ----------

@app.post("/panel/command")
def panel_command():

    if not panel_logged_in():
        return jsonify({
            "error": "Login required"
        }), 401

    data = request.get_json(silent=True) or {}

    command = str(
        data.get("command", "")
    ).strip().lower()

    allowed = {
        "status",
        "lock",
        "sleep",
        "open_notepad",
        "open_calculator",
        "open_paint",
        "open_explorer",
    }

    if command not in allowed:

        return jsonify({
            "error": "Command not allowed"
        }), 400

    with lock:

        pending_commands.append({
            "id": str(time.time_ns()),
            "command": command
        })

    return jsonify({
        "status": "queued",
        "command": command
    })


# ---------- LAPTOP → RELAY ----------

@app.get("/poll")
def poll():

    if not relay_authorized():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    with lock:

        commands = pending_commands[:]

        pending_commands.clear()

    return jsonify({
        "commands": commands
    })


# ---------- RELAY STATUS ----------

@app.get("/health")
def health():

    return jsonify({
        "status": "ok"
    })


@app.get("/status")
def status():

    if not relay_authorized():

        return jsonify({
            "error": "Unauthorized"
        }), 401

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
