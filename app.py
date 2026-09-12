import os
import io
import time
import uuid
import threading

from flask import (
    Flask,
    request,
    jsonify,
    session,
    redirect,
    render_template_string,
    send_file
)

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

RELAY_KEY = os.environ.get("RELAY_KEY", "")
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "")
PORT = int(os.environ.get("PORT", "10000"))

app.secret_key = os.environ.get(
    "PANEL_PASSWORD",
    "change-this-secret"
)

# =========================================================
# STORAGE
# =========================================================

pending_commands = []
available_apps = []

lock = threading.Lock()
apps_lock = threading.Lock()

# Screenshot results
screenshot_results = {}
screenshot_lock = threading.Lock()

# Screenshot result maximum lifetime
SCREENSHOT_TTL = 300


# =========================================================
# SECURITY HELPERS
# =========================================================

def relay_authorized():
    return (
        RELAY_KEY
        and request.headers.get("X-Relay-Key", "") == RELAY_KEY
    )


def panel_logged_in():
    return session.get("logged_in") is True


# =========================================================
# APP ICONS
# =========================================================

def get_app_icon(name):
    name_lower = name.lower()

    icons = [
        ("whatsapp", "💬"),
        ("instagram", "📸"),
        ("chrome", "🌐"),
        ("edge", "🌐"),
        ("firefox", "🦊"),
        ("visual studio code", "💻"),
        ("vs code", "💻"),
        ("spotify", "🎵"),
        ("discord", "🎮"),
        ("krita", "🎨"),
        ("paint", "🎨"),
        ("steam", "🎮"),
        ("epic games", "🎮"),
        ("calculator", "🧮"),
        ("notepad", "📝"),
        ("explorer", "📁"),
        ("file explorer", "📁"),
        ("vlc", "🎬"),
        ("zoom", "📹"),
        ("telegram", "✈️"),
        ("github", "🐙"),
        ("office", "📊"),
        ("word", "📘"),
        ("excel", "📗"),
        ("powerpoint", "📙"),
    ]

    for keyword, icon in icons:
        if keyword in name_lower:
            return icon

    return "📦"


# =========================================================
# LOGIN PAGE
# =========================================================

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Laptop Remote Login</title>

    <style>
        body {
            margin: 0;
            background: #111827;
            color: white;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }

        .box {
            width: 90%;
            max-width: 380px;
            background: #1f2937;
            padding: 25px;
            border-radius: 18px;
            box-sizing: border-box;
        }

        h1 {
            text-align: center;
        }

        input {
            width: 100%;
            box-sizing: border-box;
            padding: 14px;
            margin-top: 15px;
            border-radius: 10px;
            border: none;
            font-size: 16px;
        }

        button {
            width: 100%;
            padding: 14px;
            margin-top: 15px;
            border: none;
            border-radius: 10px;
            background: #2563eb;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }

        .error {
            color: #f87171;
            text-align: center;
            margin-top: 12px;
        }
    </style>
</head>

<body>

<div class="box">

    <h1>🔐 Laptop Remote</h1>

    <form method="POST">

        <input
            type="password"
            name="password"
            placeholder="Panel Password"
            required
        >

        <button type="submit">
            Login
        </button>

    </form>

    {% if error %}
        <div class="error">
            {{ error }}
        </div>
    {% endif %}

</div>

</body>
</html>
"""


# =========================================================
# MAIN PANEL
# =========================================================

PANEL_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Laptop Remote</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0f172a;
    color: white;
    font-family: Arial, sans-serif;
}

.container {
    width: 94%;
    max-width: 800px;
    margin: auto;
    padding: 20px 0 40px;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.header h1 {
    margin: 0;
}

.logout {
    background: #dc2626;
    color: white;
    border: none;
    padding: 9px 14px;
    border-radius: 9px;
    cursor: pointer;
}

.card {
    background: #1e293b;
    padding: 18px;
    border-radius: 16px;
    margin-bottom: 18px;
}

.card h2 {
    margin-top: 0;
}

.quick-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
}

.quick-button {
    border: none;
    border-radius: 12px;
    padding: 14px 8px;
    color: white;
    background: #334155;
    font-size: 15px;
    cursor: pointer;
}

.quick-button:hover {
    background: #475569;
}

.status-button {
    background: #2563eb;
}

.danger-button {
    background: #dc2626;
}

.warning-button {
    background: #b45309;
}

.screenshot-button {
    background: #7c3aed;
}

.apps-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    max-height: 600px;
    overflow-y: auto;
}

.app-button {
    display: flex;
    align-items: center;
    gap: 10px;
    text-align: left;
    background: #334155;
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px;
    cursor: pointer;
    min-height: 55px;
}

.app-button:hover {
    background: #475569;
}

.app-icon {
    font-size: 24px;
    flex-shrink: 0;
}

.app-name {
    font-size: 14px;
    word-break: break-word;
}

.refresh-button {
    width: 100%;
    padding: 12px;
    margin-bottom: 12px;
    border: none;
    border-radius: 10px;
    background: #0ea5e9;
    color: white;
    font-size: 15px;
    cursor: pointer;
}

.result {
    margin-top: 15px;
    background: #020617;
    border-radius: 12px;
    padding: 12px;
    min-height: 45px;
    word-break: break-word;
}

.result img {
    display: block;
    width: 100%;
    max-width: 100%;
    border-radius: 10px;
}

#touchpad {
    height: 300px;
    margin: 20px auto;
    max-width: 600px;
    background: #222;
    border: 2px solid #444;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #aaa;
    touch-action: none;
    user-select: none;
}

.count {
    color: #94a3b8;
    font-size: 14px;
    margin-bottom: 12px;
}

@media (max-width: 500px) {

    .quick-grid {
        grid-template-columns: 1fr 1fr;
    }

    .apps-grid {
        grid-template-columns: 1fr;
    }

}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        <h1>💻 Laptop Remote</h1>

        <button
            class="logout"
            onclick="location.href='/logout'"
        >
            Logout
        </button>

    </div>


    <!-- QUICK CONTROLS -->

    <div class="card">

        <h2>⚡ Quick Controls</h2>

        <div class="quick-grid">

            <button
                class="quick-button status-button"
                onclick="sendCommand('status')"
            >
                📊 Status
            </button>

            <button
                class="quick-button danger-button"
                onclick="sendCommand('lock')"
            >
                🔒 Lock Laptop
            </button>

            <button
                class="quick-button warning-button"
                onclick="sendCommand('sleep')"
            >
                😴 Sleep Laptop
            </button>

            <button
                class="quick-button"
                onclick="sendCommand('open_notepad')"
            >
                📝 Notepad
            </button>

            <button
                class="quick-button"
                onclick="sendCommand('open_calculator')"
            >
                🧮 Calculator
            </button>

            <button
                class="quick-button"
                onclick="sendCommand('open_paint')"
            >
                🎨 Paint
            </button>

            <button
                class="quick-button"
                onclick="sendCommand('open_explorer')"
            >
                📁 Explorer
            </button>

            <button
                class="quick-button screenshot-button"
                onclick="takeScreenshot()"
            >
                📸 Screenshot
            </button>
           
            <div id="touchpad">
                 🖱️ Touchpad
            </div>

            <button class="quick-button" onclick="sendCommand('left_click')">
                    👆 Test Left Click
            </button>

            <button class="quick-button" onclick="sendCommand('right_click')">
                    👉 Test Right Click
            </button>

        </div>

        <div id="result" class="result">
            Ready.
        </div>

    </div>


    <!-- INSTALLED APPS -->

    <div class="card">

        <h2>📦 Installed Apps</h2>

        <div id="appCount" class="count">
            Loading apps...
        </div>

        <button
            class="refresh-button"
            onclick="loadApps()"
        >
            🔄 Refresh Apps
        </button>

        <div
            id="apps"
            class="apps-grid"
        ></div>

    </div>

</div>


<script>


// =========================================================
// RESULT BOX
// =========================================================

function showResult(message) {

    document.getElementById("result").textContent = message;

}


// =========================================================
// SEND NORMAL COMMAND
// =========================================================

async function sendCommand(command) {

    showResult("⏳ Sending command...");

    try {

        const response = await fetch(
            "/panel/command",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    command: command
                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            showResult(
                "❌ " +
                (data.error || "Command failed")
            );

            return;
        }


        if (command === "status" && data.command_id) {

            showResult(
                "✅ Status command sent."
            );

        } else {

            showResult(
                "✅ " +
                (data.status || "Command queued")
            );

        }

    }

    catch (error) {

        showResult(
            "❌ Connection error"
        );

    }

}


// =========================================================
// OPEN DISCOVERED APP
// =========================================================

async function openDiscoveredApp(appId, appName) {

    showResult(
        "⏳ Opening " + appName + "..."
    );


    try {

        const response = await fetch(
            "/panel/command",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    command: "open_app",
                    app_id: appId
                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            showResult(
                "❌ " +
                (data.error || "Could not open app")
            );

            return;
        }


        showResult(
            "✅ " + appName + " queued"
        );

    }

    catch (error) {

        showResult(
            "❌ Connection error"
        );

    }

}


// =========================================================
// LOAD INSTALLED APPS
// =========================================================

async function loadApps() {

    const appsContainer =
        document.getElementById("apps");

    const count =
        document.getElementById("appCount");


    count.textContent =
        "⏳ Loading apps...";


    appsContainer.innerHTML = "";


    try {

        const response =
            await fetch(
                "/panel/apps",
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            count.textContent =
                "❌ Failed to load apps";

            return;
        }


        const apps =
            data.apps || [];


        count.textContent =
            apps.length +
            " apps available";


        if (apps.length === 0) {

            appsContainer.innerHTML =
                "<div>No apps registered yet.</div>";

            return;
        }


        for (const app of apps) {

            const button =
                document.createElement("button");

            button.className =
                "app-button";


            const icon =
                document.createElement("span");

            icon.className =
                "app-icon";

            icon.textContent =
                app.icon || "📦";


            const name =
                document.createElement("span");

            name.className =
                "app-name";

            name.textContent =
                app.name;


            button.appendChild(icon);
            button.appendChild(name);


            button.onclick =
                function() {

                    openDiscoveredApp(
                        app.id,
                        app.name
                    );

                };


            appsContainer.appendChild(
                button
            );

        }

    }

    catch (error) {

        count.textContent =
            "❌ Connection error";

    }

}


// =========================================================
// TAKE REMOTE SCREENSHOT
// =========================================================

async function takeScreenshot() {

    showResult(
        "⏳ Taking screenshot..."
    );


    try {

        const response =
            await fetch(
                "/panel/command",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        command: "screenshot"
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            showResult(
                "❌ " +
                (data.error ||
                 "Screenshot command failed")
            );

            return;
        }


        const commandId =
            data.command_id;


        if (!commandId) {

            showResult(
                "❌ Screenshot command ID missing"
            );

            return;
        }


        const maxAttempts = 30;


        for (
            let attempt = 0;
            attempt < maxAttempts;
            attempt++
        ) {

            await new Promise(
                resolve =>
                    setTimeout(resolve, 1000)
            );


            const imageResponse =
                await fetch(
                    "/panel/screenshot/" +
                    encodeURIComponent(commandId),
                    {
                        cache: "no-store"
                    }
                );


            // Laptop is still processing
            if (
                imageResponse.status === 202
            ) {

                showResult(
                    "⏳ Waiting for laptop screenshot..."
                );

                continue;
            }


            // Something went wrong
            if (!imageResponse.ok) {

                let errorData = {};

                try {

                    errorData =
                        await imageResponse.json();

                } catch (e) {}


                showResult(
                    "❌ " +
                    (
                        errorData.error ||
                        "Screenshot failed"
                    )
                );

                return;
            }


            // Screenshot received
            const blob =
                await imageResponse.blob();


            const imageUrl =
                URL.createObjectURL(blob);


            const result =
                document.getElementById(
                    "result"
                );


            result.innerHTML = "";


            const image =
                document.createElement("img");


            image.src =
                imageUrl;


            image.alt =
                "Laptop Screenshot";


            result.appendChild(image);


            return;

        }


        showResult(
            "⏱️ Screenshot timed out. Make sure laptop is online."
        );

    }

    catch (error) {

        showResult(
            "❌ Connection error"
        );

    }

}


// =========================================================
// TOUCHPAD MOUSE MOVEMENT
// =========================================================

const touchpad =
    document.getElementById("touchpad");

let lastTouchX = 0;
let lastTouchY = 0;
let touchMoved = false;
let rightClickGesture = false;

let movementDX = 0;
let movementDY = 0;

let movementTimer = null;


touchpad.addEventListener(
    "touchstart",
    function(event) {

        event.preventDefault();

        // Two fingers detected
        if (event.touches.length === 2) {
            rightClickGesture = true;
            touchMoved = false;
            return;
        }

        // Start normal one-finger movement
        if (event.touches.length === 1) {

            rightClickGesture = false;

            const touch =
                event.touches[0];

            lastTouchX =
                touch.clientX;

            lastTouchY =
                touch.clientY;

            touchMoved = false;
        }

    },
    { passive: false }
);


touchpad.addEventListener(
    "touchmove",
    function(event) {

        event.preventDefault();

        if (rightClickGesture) {
            return;
        }

        const touch =
            event.touches[0];

        const dx =
            touch.clientX -
            lastTouchX;

        const dy =
            touch.clientY -
            lastTouchY;


        lastTouchX =
            touch.clientX;

        lastTouchY =
            touch.clientY;

        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
            touchMoved = true;
        }    


        movementDX += dx;
        movementDY += dy;

        if (!movementTimer) {

            movementTimer =
                setTimeout(
                    sendMouseMovement,
                    10
                );

        }

    },
    { passive: false }
);

touchpad.addEventListener(
    "touchend",
    async function(event) {

        event.preventDefault();

        // Two-finger tap = Right Click
        if (rightClickGesture) {

            // Wait until both fingers are released
            if (event.touches.length === 0) {

                try {
                    await fetch(
                        "/panel/command",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body: JSON.stringify({
                                command: "right_click"
                            })
                        }
                    );
                } catch (error) {
                    console.log(
                        "Right click error:",
                        error
                    );
                }

                rightClickGesture = false;
                touchMoved = false;
            }

            return;
        }

        // One-finger tap = Left Click
        if (!touchMoved && event.touches.length === 0) {

            try {
                await fetch(
                    "/panel/command",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            command: "left_click"
                        })
                    }
                );
            } catch (error) {
                console.log(
                    "Left click error:",
                    error
                );
            }
        }

    },
    { passive: false }
);

async function sendMouseMovement() {

    movementTimer = null;


    const dx =
        movementDX;

    const dy =
        movementDY;


    movementDX = 0;
    movementDY = 0;


    if (dx === 0 && dy === 0) {
        return;
    }


    try {

        await fetch(
            "/panel/command",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    command: "move_mouse",
                    dx: dx,
                    dy: dy
                })
            }
        );

    }

    catch (error) {

        console.log(
            "Mouse movement error:",
            error
        );

    }

}


// =========================================================
// LOAD APPS WHEN PAGE OPENS
// =========================================================

loadApps();

</script>

</body>

</html>
"""


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    if not panel_logged_in():
        return redirect("/login")

    return render_template_string(
        PANEL_HTML
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        password = request.form.get("password", "")

        if (
            PANEL_PASSWORD
            and password == PANEL_PASSWORD
        ):

            session["logged_in"] = True

            return redirect("/")

        return render_template_string(
            LOGIN_HTML,
            error="❌ Incorrect password"
        )


    return render_template_string(
        LOGIN_HTML
    )


# =========================================================
# LOGOUT
# =========================================================

@app.get("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================================
# GET INSTALLED APPS
# =========================================================

@app.get("/panel/apps")
def panel_apps():

    if not panel_logged_in():

        return jsonify({
            "error": "Login required"
        }), 401


    with apps_lock:

        apps_copy = [
            {
                "id": app_item["id"],
                "name": app_item["name"],
                "icon": get_app_icon(
                    app_item["name"]
                )
            }

            for app_item in available_apps
        ]


    return jsonify({
        "apps": apps_copy
    })


# =========================================================
# REGISTER APPS FROM LAPTOP
# =========================================================

@app.post("/register_apps")
def register_apps():

    if not relay_authorized():

        return jsonify({
            "error": "Unauthorized"
        }), 401


    data = request.get_json(
        silent=True
    ) or {}


    apps = data.get("apps", [])


    if not isinstance(apps, list):

        return jsonify({
            "error": "apps must be a list"
        }), 400


    cleaned = []
    seen = set()


    for item in apps:

        if not isinstance(
            item,
            dict
        ):
            continue


        app_id = str(
            item.get("id", "")
        ).strip()


        name = str(
            item.get("name", "")
        ).strip()


        if not app_id or not name:
            continue


        # Basic size protection
        if len(app_id) > 100:
            continue

        if len(name) > 300:
            continue


        if app_id in seen:
            continue


        seen.add(app_id)


        cleaned.append({
            "id": app_id,
            "name": name
        })


    with apps_lock:

        available_apps.clear()

        available_apps.extend(
            cleaned
        )


    return jsonify({
        "status": "registered",
        "count": len(cleaned)
    })


# =========================================================
# QUEUE COMMAND FROM PHONE
# =========================================================

@app.post("/panel/command")
def panel_command():

    if not panel_logged_in():

        return jsonify({
            "error": "Login required"
        }), 401


    data = request.get_json(
        silent=True
    ) or {}


    command = str(
        data.get("command", "")
    ).strip()


    allowed_commands = {
        "status",
        "lock",
        "sleep",
        "open_notepad",
        "open_calculator",
        "open_paint",
        "open_explorer",
        "open_app",
        "screenshot",
        "move_mouse",
        "left_click",
        "right_click",
    }


    if command not in allowed_commands:

        return jsonify({
            "error": "Command not allowed"
        }), 400


    command_item = {
        "id": uuid.uuid4().hex,
        "command": command,
        "created": time.time()
    }

    if command == "move_mouse":

        command_item["dx"] = data.get("dx", 0)
        command_item["dy"] = data.get("dy", 0)

    
    # =====================================================
    # OPEN DISCOVERED APP
    # =====================================================

    if command == "open_app":

        app_id = str(
            data.get("app_id", "")
        ).strip()


        if not app_id:

            return jsonify({
                "error": "app_id required"
            }), 400


        with apps_lock:

            valid_ids = {
                app_item["id"]
                for app_item in available_apps
            }


        if app_id not in valid_ids:

            return jsonify({
                "error": "Unknown app"
            }), 400


        command_item["app_id"] = app_id


    # =====================================================
    # SCREENSHOT TRACKING
    # =====================================================

    if command == "screenshot":

        with screenshot_lock:

            screenshot_results[
                command_item["id"]
            ] = {
                "status": "pending",
                "created": time.time()
            }


    # =====================================================
    # QUEUE COMMAND
    # =====================================================

    with lock:

        pending_commands.append(
            command_item
        )


    response_data = {
        "status": "queued",
        "command": command
    }


    if command == "screenshot":

        response_data[
            "command_id"
        ] = command_item["id"]


    return jsonify(
        response_data
    )


# =========================================================
# LAPTOP POLLS FOR COMMANDS
# =========================================================

@app.get("/poll")
def poll():

    if not relay_authorized():

        return jsonify({
            "error": "Unauthorized"
        }), 401


    with lock:

        commands = list(
            pending_commands
        )

        pending_commands.clear()


    return jsonify({
        "commands": commands
    })


# =========================================================
# LAPTOP UPLOADS SCREENSHOT
# =========================================================

@app.post("/upload_screenshot")
def upload_screenshot():

    if not relay_authorized():

        return jsonify({
            "error": "Unauthorized"
        }), 401


    command_id = request.args.get(
        "command_id",
        ""
    ).strip()


    if not command_id:

        return jsonify({
            "error": "command_id required"
        }), 400


    image = request.get_data(
        cache=False
    )


    # Maximum screenshot size: 10 MB
    if (
        not image
        or len(image) > 10 * 1024 * 1024
    ):

        return jsonify({
            "error": "Invalid screenshot"
        }), 400


    with screenshot_lock:

        if command_id not in screenshot_results:

            return jsonify({
                "error": "Unknown screenshot command"
            }), 404


        screenshot_results[
            command_id
        ] = {
            "status": "ready",
            "image": image,
            "created": time.time()
        }


    return jsonify({
        "status": "stored"
    })


# =========================================================
# PHONE GETS SCREENSHOT
# =========================================================

@app.get("/panel/screenshot/<command_id>")
def panel_screenshot(command_id):

    if not panel_logged_in():

        return jsonify({
            "error": "Login required"
        }), 401


    command_id = command_id.strip()


    with screenshot_lock:

        result = screenshot_results.get(
            command_id
        )


    if not result:

        return jsonify({
            "error": "Screenshot not found"
        }), 404


    # Expired
    if (
        time.time() -
        result["created"]
        > SCREENSHOT_TTL
    ):

        with screenshot_lock:

            screenshot_results.pop(
                command_id,
                None
            )


        return jsonify({
            "error": "Screenshot expired"
        }), 410


    # Laptop hasn't uploaded it yet
    if result["status"] == "pending":

        return jsonify({
            "status": "pending"
        }), 202


    # Screenshot ready
    return send_file(
        io.BytesIO(
            result["image"]
        ),
        mimetype="image/jpeg",
        download_name="screenshot.jpg"
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return jsonify({
        "status": "ok"
    })


# =========================================================
# STATUS
# =========================================================

@app.get("/status")
def status():

    return jsonify({
        "status": "online",
        "apps": len(available_apps),
        "pending_commands": len(
            pending_commands
        )
    })


# =========================================================
# CLEAN OLD SCREENSHOT RESULTS
# =========================================================

def screenshot_cleanup_loop():

    while True:

        try:

            now = time.time()


            with screenshot_lock:

                expired = [

                    command_id

                    for command_id, result
                    in screenshot_results.items()

                    if (
                        now -
                        result["created"]
                        > SCREENSHOT_TTL
                    )

                ]


                for command_id in expired:

                    screenshot_results.pop(
                        command_id,
                        None
                    )


        except Exception:

            pass


        time.sleep(60)


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    print(
        "Laptop Remote Relay starting..."
    )

    threading.Thread(
        target=screenshot_cleanup_loop,
        daemon=True
    ).start()


    print(
        "Laptop Remote Relay started."
    )

    print(
        f"Listening on port {PORT}"
    )


    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
