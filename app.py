import os
import time
import threading

from flask import (
    Flask,
    request,
    jsonify,
    render_template_string,
    session,
    send_file
)

from io import BytesIO


app = Flask(__name__)


# ============================================================
# CONFIG
# ============================================================

RELAY_KEY = os.environ.get(
    "RELAY_KEY",
    ""
)

PANEL_PASSWORD = os.environ.get(
    "PANEL_PASSWORD",
    ""
)

PORT = int(
    os.environ.get(
        "PORT",
        "10000"
    )
)


app.secret_key = os.environ.get(
    "PANEL_PASSWORD",
    "change-this-secret"
)


# ============================================================
# STORAGE
# ============================================================

pending_commands = []

available_apps = []

screenshot_results = {}

lock = threading.Lock()

apps_lock = threading.Lock()

screenshots_lock = threading.Lock()


# ============================================================
# RELAY SECURITY
# ============================================================

def relay_authorized():

    return (
        bool(RELAY_KEY)
        and
        request.headers.get(
            "X-Relay-Key"
        ) == RELAY_KEY
    )


# ============================================================
# PANEL SECURITY
# ============================================================

def panel_logged_in():

    return (
        session.get(
            "panel_logged_in"
        ) is True
    )


# ============================================================
# APP ICONS
# ============================================================

def get_app_icon(name):

    name_lower = name.lower()


    if "whatsapp" in name_lower:
        return "💬"

    if "instagram" in name_lower:
        return "📷"

    if "chrome" in name_lower:
        return "🌐"

    if "edge" in name_lower:
        return "🌐"

    if "firefox" in name_lower:
        return "🌐"

    if "browser" in name_lower:
        return "🌐"

    if "visual studio code" in name_lower:
        return "💻"

    if "vs code" in name_lower:
        return "💻"

    if "spotify" in name_lower:
        return "🎵"

    if "discord" in name_lower:
        return "💬"

    if "krita" in name_lower:
        return "🎨"

    if "paint" in name_lower:
        return "🎨"

    if "steam" in name_lower:
        return "🎮"

    if "epic games" in name_lower:
        return "🎮"

    if "calculator" in name_lower:
        return "🧮"

    if "notepad" in name_lower:
        return "📝"

    if "explorer" in name_lower:
        return "📁"

    if "file explorer" in name_lower:
        return "📁"

    if "vlc" in name_lower:
        return "🎬"

    if "zoom" in name_lower:
        return "📹"

    if "telegram" in name_lower:
        return "💬"

    if "github" in name_lower:
        return "🐙"

    if "office" in name_lower:
        return "📄"

    if "word" in name_lower:
        return "📘"

    if "excel" in name_lower:
        return "📊"

    if "powerpoint" in name_lower:
        return "📽️"

    return "📱"


# ============================================================
# PHONE PANEL
# ============================================================

PANEL_HTML = """
<!DOCTYPE html>

<html>

<head>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <title>Laptop Remote</title>


    <style>

        * {
            box-sizing: border-box;
        }


        body {

            margin: 0;

            padding: 20px;

            font-family: Arial, sans-serif;

            background: #111;

            color: white;

        }


        .container {

            width: 100%;

            max-width: 650px;

            margin: auto;

        }


        h1 {

            text-align: center;

            margin-bottom: 25px;

        }


        h2 {

            margin-top: 30px;

            margin-bottom: 12px;

        }


        button {

            width: 100%;

            padding: 15px;

            margin: 6px 0;

            border: none;

            border-radius: 12px;

            font-size: 17px;

            cursor: pointer;

            background: #222;

            color: white;

        }


        button:active {

            transform: scale(0.98);

        }


        .quick-button {

            background: #1d1d1d;

        }


        .screenshot-button {

            background: #252525;

            border: 1px solid #444;

        }


        .app-button {

            display: flex;

            align-items: center;

            text-align: left;

            gap: 14px;

            background: #1c1c1c;

            border: 1px solid #333;

        }


        .app-icon {

            font-size: 28px;

            width: 38px;

            text-align: center;

            flex-shrink: 0;

        }


        .app-name {

            font-size: 16px;

            word-break: break-word;

        }


        #result {

            margin-top: 20px;

            padding: 15px;

            border-radius: 12px;

            background: #222;

            text-align: center;

            word-break: break-word;

        }


        #screenshot-preview {

            margin-top: 15px;

        }


        #screenshot-preview img {

            width: 100%;

            max-width: 100%;

            height: auto;

            border-radius: 12px;

            border: 1px solid #444;

            display: block;

        }


        .apps-header {

            display: flex;

            justify-content: space-between;

            align-items: center;

            gap: 10px;

        }


        .refresh-button {

            width: auto;

            padding: 10px 14px;

            margin: 0;

            font-size: 14px;

            background: #333;

        }


        #apps-list {

            margin-top: 10px;

        }


        .empty {

            padding: 20px;

            text-align: center;

            color: #aaa;

            background: #1c1c1c;

            border-radius: 12px;

        }


        .count {

            color: #aaa;

            font-size: 14px;

            margin-bottom: 10px;

        }


        .logout {

            margin-top: 30px;

            background: #2a1616;

        }

    </style>

</head>


<body>


<div class="container">


    <h1>💻 Laptop Remote</h1>


    <!-- QUICK CONTROLS -->

    <h2>⚡ Quick Controls</h2>


    <button class="quick-button"
            onclick="sendCommand('status')">

        🟢 Status

    </button>


    <button class="screenshot-button"
            onclick="takeScreenshot()">

        📸 Screenshot

    </button>


    <button class="quick-button"
            onclick="sendCommand('lock')">

        🔒 Lock Laptop

    </button>


    <button class="quick-button"
            onclick="sendCommand('sleep')">

        😴 Sleep Laptop

    </button>


    <button class="quick-button"
            onclick="sendCommand('open_notepad')">

        📝 Notepad

    </button>


    <button class="quick-button"
            onclick="sendCommand('open_calculator')">

        🧮 Calculator

    </button>


    <button class="quick-button"
            onclick="sendCommand('open_paint')">

        🎨 Paint

    </button>


    <button class="quick-button"
            onclick="sendCommand('open_explorer')">

        📁 Explorer

    </button>


    <!-- SCREENSHOT RESULT -->

    <div id="screenshot-preview"></div>


    <!-- INSTALLED APPS -->

    <div class="apps-header">

        <h2>📱 Installed Apps</h2>

        <button class="refresh-button"
                onclick="loadApps()">

            🔄 Refresh

        </button>

    </div>


    <div id="app-count"
         class="count">

        Loading apps...

    </div>


    <div id="apps-list">

        <div class="empty">

            ⏳ Loading discovered apps...

        </div>

    </div>


    <!-- RESULT -->

    <div id="result">

        Ready...

    </div>


    <!-- LOGOUT -->

    <button class="logout"
            onclick="logout()">

        🚪 Logout

    </button>


</div>


<script>


// ============================================================
// RESULT
// ============================================================

function showResult(message) {

    document.getElementById(
        "result"
    ).innerText = message;

}


// ============================================================
// SEND NORMAL COMMAND
// ============================================================

async function sendCommand(command) {

    showResult(
        "⏳ Sending command..."
    );


    try {

        const response = await fetch(
            "/panel/command",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    command: command
                })

            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            showResult(
                "❌ " +
                (
                    data.error ||
                    "Command failed"
                )
            );

            return;
        }


        showResult(
            "✅ " +
            (
                data.status ||
                "Command queued"
            )
        );


    } catch (error) {

        showResult(
            "❌ Connection error"
        );

    }

}


// ============================================================
// SCREENSHOT
// ============================================================

async function takeScreenshot() {

    showResult(
        "📸 Requesting laptop screenshot..."
    );


    document.getElementById(
        "screenshot-preview"
    ).innerHTML = "";


    try {

        const response = await fetch(
            "/panel/command",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    command:
                        "screenshot"
                })

            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            showResult(
                "❌ " +
                (
                    data.error ||
                    "Screenshot request failed"
                )
            );

            return;
        }


        const commandId =
            data.command_id;


        if (!commandId) {

            showResult(
                "❌ Screenshot ID missing"
            );

            return;
        }


        showResult(
            "⏳ Capturing screenshot..."
        );


        await waitForScreenshot(
            commandId
        );


    } catch (error) {

        showResult(
            "❌ Connection error"
        );

    }

}


// ============================================================
// WAIT FOR SCREENSHOT
// ============================================================

async function waitForScreenshot(
    commandId
) {

    const maxAttempts = 30;

    const delay = 1000;


    for (
        let attempt = 0;
        attempt < maxAttempts;
        attempt++
    ) {

        try {

            const response =
                await fetch(
                    "/panel/screenshot/" +
                    encodeURIComponent(
                        commandId
                    )
                );


            if (response.ok) {

                const blob =
                    await response.blob();


                const imageUrl =
                    URL.createObjectURL(
                        blob
                    );


                document.getElementById(
                    "screenshot-preview"
                ).innerHTML =

                    '<img src="' +
                    imageUrl +
                    '" alt="Laptop Screenshot">';


                showResult(
                    "✅ Screenshot received"
                );

                return;
            }


            if (
                response.status !== 202
            ) {

                let data = {};

                try {
                    data =
                        await response.json();
                } catch (e) {}


                showResult(
                    "❌ " +
                    (
                        data.error ||
                        "Screenshot unavailable"
                    )
                );

                return;
            }


        } catch (error) {

            showResult(
                "❌ Connection error"
            );

            return;
        }


        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    delay
                )
        );

    }


    showResult(
        "❌ Screenshot timed out"
    );

}


// ============================================================
// OPEN DISCOVERED APP
// ============================================================

async function openDiscoveredApp(
    appId,
    appName
) {

    showResult(
        "⏳ Opening " +
        appName +
        "..."
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

                        command:
                            "open_app",

                        app_id:
                            appId

                    })

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            showResult(
                "❌ " +
                (
                    data.error ||
                    "Could not open app"
                )
            );

            return;
        }


        showResult(
            "✅ " +
            appName +
            " command sent"
        );


    } catch (error) {

        showResult(
            "❌ Connection error"
        );

    }

}


// ============================================================
// LOAD INSTALLED APPS
// ============================================================

async function loadApps() {

    const list =
        document.getElementById(
            "apps-list"
        );

    const count =
        document.getElementById(
            "app-count"
        );


    list.innerHTML = `
        <div class="empty">
            ⏳ Loading discovered apps...
        </div>
    `;


    count.innerText =
        "Checking laptop apps...";


    try {

        const response =
            await fetch(
                "/panel/apps"
            );


        const data =
            await response.json();


        if (!response.ok) {

            list.innerHTML = `
                <div class="empty">
                    ❌ ${
                        data.error ||
                        "Could not load apps"
                    }
                </div>
            `;

            count.innerText =
                "Apps unavailable";

            return;
        }


        const apps =
            data.apps || [];


        if (apps.length === 0) {

            list.innerHTML = `
                <div class="empty">

                    📱 No discovered apps yet.

                    <br><br>

                    Make sure the laptop agent
                    is running and connected.

                </div>
            `;

            count.innerText =
                "0 apps";

            return;
        }


        count.innerText =
            apps.length +
            " apps discovered";


        list.innerHTML = "";


        for (const app of apps) {

            const button =
                document.createElement(
                    "button"
                );


            button.className =
                "app-button";


            const icon =
                document.createElement(
                    "span"
                );

            icon.className =
                "app-icon";

            icon.innerText =
                app.icon ||
                "📱";


            const name =
                document.createElement(
                    "span"
                );

            name.className =
                "app-name";

            name.innerText =
                app.name;


            button.appendChild(
                icon
            );

            button.appendChild(
                name
            );


            button.onclick =
                function() {

                    openDiscoveredApp(
                        app.id,
                        app.name
                    );

                };


            list.appendChild(
                button
            );

        }


    } catch (error) {

        list.innerHTML = `
            <div class="empty">
                ❌ Could not connect to relay.
            </div>
        `;

        count.innerText =
            "Connection failed";

    }

}


// ============================================================
// LOGOUT
// ============================================================

async function logout() {

    try {

        await fetch(
            "/logout",
            {
                method: "POST"
            }
        );

    } finally {

        window.location.href = "/";

    }

}


// ============================================================
// LOAD APPS
// ============================================================

loadApps();


</script>


</body>

</html>
"""


# ============================================================
# LOGIN HTML
# ============================================================

LOGIN_HTML = """
<!DOCTYPE html>

<html>

<head>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <title>Laptop Remote Login</title>


    <style>

        body {

            margin: 0;

            min-height: 100vh;

            display: flex;

            align-items: center;

            justify-content: center;

            background: #111;

            color: white;

            font-family: Arial, sans-serif;

            padding: 20px;

        }


        .box {

            width: 100%;

            max-width: 400px;

            background: #1c1c1c;

            padding: 25px;

            border-radius: 16px;

            text-align: center;

        }


        input {

            width: 100%;

            box-sizing: border-box;

            padding: 15px;

            margin: 15px 0;

            border-radius: 10px;

            border: 1px solid #444;

            background: #111;

            color: white;

            font-size: 16px;

        }


        button {

            width: 100%;

            padding: 15px;

            border: none;

            border-radius: 10px;

            background: #333;

            color: white;

            font-size: 17px;

            cursor: pointer;

        }


        .error {

            color: #ff7777;

            margin-bottom: 10px;

        }

    </style>

</head>


<body>


<div class="box">

    <h1>🔐 Laptop Remote</h1>

    <p>Enter your panel password</p>


    {% if error %}

        <div class="error">

            ❌ Wrong password

        </div>

    {% endif %}


    <form method="POST"
          action="/login">

        <input
            type="password"
            name="password"
            placeholder="Panel password"
            autocomplete="current-password"
            required
        >


        <button type="submit">

            🔓 Login

        </button>

    </form>

</div>


</body>

</html>
"""


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    if panel_logged_in():

        return render_template_string(
            PANEL_HTML
        )

    return render_template_string(
        LOGIN_HTML,
        error=False
    )


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login():

    password = request.form.get(
        "password",
        ""
    )


    if (
        PANEL_PASSWORD
        and password == PANEL_PASSWORD
    ):

        session[
            "panel_logged_in"
        ] = True


        return render_template_string(
            PANEL_HTML
        )


    return render_template_string(
        LOGIN_HTML,
        error=True
    ), 401


# ============================================================
# LOGOUT
# ============================================================

@app.post("/logout")
def logout():

    session.clear()


    return jsonify({
        "status":
            "logged out"
    })


# ============================================================
# GET DISCOVERED APPS
# ============================================================

@app.get("/panel/apps")
def panel_apps():

    if not panel_logged_in():

        return jsonify({
            "error":
                "Login required"
        }), 401


    with apps_lock:

        apps = [

            {
                "id":
                    app["id"],

                "name":
                    app["name"],

                "icon":
                    get_app_icon(
                        app["name"]
                    )

            }

            for app in available_apps
        ]


    apps.sort(
        key=lambda item:
            item["name"].lower()
    )


    return jsonify({

        "apps":
            apps,

        "count":
            len(apps)

    })


# ============================================================
# REGISTER APPS
# ============================================================

@app.post("/register_apps")
def register_apps():

    if not relay_authorized():

        return jsonify({
            "error":
                "Unauthorized"
        }), 401


    data = request.get_json(
        silent=True
    ) or {}


    incoming_apps =
        data.get(
            "apps",
            []
        )


    if not isinstance(
        incoming_apps,
        list
    ):

        return jsonify({
            "error":
                "Invalid apps data"
        }), 400


    clean_apps = []


    for item in incoming_apps:

        if not isinstance(
            item,
            dict
        ):
            continue


        app_id = str(
            item.get(
                "id",
                ""
            )
        ).strip()


        app_name = str(
            item.get(
                "name",
                ""
            )
        ).strip()


        if not app_id or not app_name:
            continue


        if len(app_id) > 100:
            continue


        if len(app_name) > 300:
            continue


        clean_apps.append({

            "id":
                app_id,

            "name":
                app_name

        })


    unique_apps = {}


    for item in clean_apps:

        unique_apps[
            item["id"]
        ] = item


    with apps_lock:

        available_apps.clear()

        available_apps.extend(
            unique_apps.values()
        )


    print(
        f"📱 Received "
        f"{len(unique_apps)} apps from laptop."
    )


    return jsonify({

        "status":
            "Apps registered",

        "count":
            len(unique_apps)

    })


# ============================================================
# PHONE COMMAND QUEUE
# ============================================================

@app.post("/panel/command")
def panel_command():

    if not panel_logged_in():

        return jsonify({
            "error":
                "Login required"
        }), 401


    data = request.get_json(
        silent=True
    ) or {}


    command = str(
        data.get(
            "command",
            ""
        )
    ).strip().lower()


    allowed = {

        "status",

        "screenshot",

        "lock",

        "sleep",

        "open_notepad",

        "open_calculator",

        "open_paint",

        "open_explorer",

        "open_app",

    }


    if command not in allowed:

        return jsonify({
            "error":
                "Command not allowed"
        }), 400


    command_id = str(
        time.time_ns()
    )


    command_item = {

        "id":
            command_id,

        "command":
            command

    }


    # ========================================================
    # SCREENSHOT
    # ========================================================

    if command == "screenshot":

        with screenshots_lock:

            screenshot_results[
                command_id
            ] = {

                "status":
                    "pending",

                "created_at":
                    time.time()

            }


    # ========================================================
    # DISCOVERED APP
    # ========================================================

    if command == "open_app":

        app_id = str(
            data.get(
                "app_id",
                ""
            )
        ).strip()


        if not app_id:

            return jsonify({
                "error":
                    "App ID required"
            }), 400


        with apps_lock:

            registered = any(

                app["id"] == app_id

                for app in available_apps

            )


        if not registered:

            return jsonify({
                "error":
                    "App is not currently registered"
            }), 400


        command_item[
            "app_id"
        ] = app_id


    # ========================================================
    # QUEUE COMMAND
    # ========================================================

    with lock:

        pending_commands.append(
            command_item
        )


    if command == "screenshot":

        return jsonify({

            "status":
                "Screenshot queued",

            "command_id":
                command_id

        })


    return jsonify({

        "status":
            "queued",

        "command":
            command

    })


# ============================================================
# UPLOAD SCREENSHOT FROM LAPTOP
# ============================================================

@app.post("/upload_screenshot")
def upload_screenshot():

    if not relay_authorized():

        return jsonify({
            "error":
                "Unauthorized"
        }), 401


    screenshot_id = request.headers.get(
        "X-Screenshot-ID",
        ""
    ).strip()


    if not screenshot_id:

        return jsonify({
            "error":
                "Screenshot ID missing"
        }), 400


    image_data = request.get_data()


    if not image_data:

        return jsonify({
            "error":
                "Empty screenshot"
        }), 400


    # Keep screenshot size bounded.

    if len(image_data) > 15 * 1024 * 1024:

        return jsonify({
            "error":
                "Screenshot too large"
        }), 413


    with screenshots_lock:

        screenshot_results[
            screenshot_id
        ] = {

            "status":
                "ready",

            "data":
                image_data,

            "created_at":
                time.time()

        }


    return jsonify({
        "status":
            "Screenshot received"
    })


# ============================================================
# GET SCREENSHOT FOR PHONE
# ============================================================

@app.get(
    "/panel/screenshot/<screenshot_id>"
)
def get_screenshot(screenshot_id):

    if not panel_logged_in():

        return jsonify({
            "error":
                "Login required"
        }), 401


    screenshot_id = str(
        screenshot_id
    ).strip()


    with screenshots_lock:

        result = screenshot_results.get(
            screenshot_id
        )


    if not result:

        return jsonify({
            "error":
                "Screenshot not found"
        }), 404


    if result["status"] == "pending":

        return jsonify({
            "status":
                "pending"
        }), 202


    image_data = result.get(
        "data"
    )


    if not image_data:

        return jsonify({
            "error":
                "Screenshot data missing"
        }), 500


    return send_file(

        BytesIO(image_data),

        mimetype="image/jpeg",

        download_name=
            "laptop_screenshot.jpg"

    )


# ============================================================
# CLEAN OLD SCREENSHOTS
# ============================================================

def screenshot_cleanup_loop():

    while True:

        time.sleep(60)

        now = time.time()


        with screenshots_lock:

            expired = [

                screenshot_id

                for screenshot_id, result
                in screenshot_results.items()

                if now -
                   result.get(
                       "created_at",
                       now
                   ) > 300

            ]


            for screenshot_id in expired:

                screenshot_results.pop(
                    screenshot_id,
                    None
                )


# ============================================================
# LAPTOP POLLING
# ============================================================

@app.get("/poll")
def poll():

    if not relay_authorized():

        return jsonify({
            "error":
                "Unauthorized"
        }), 401


    with lock:

        commands = pending_commands[:]

        pending_commands.clear()


    return jsonify({
        "commands":
            commands
    })


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return jsonify({
        "status":
            "ok"
    })


# ============================================================
# RELAY STATUS
# ============================================================

@app.get("/status")
def status():

    if not relay_authorized():

        return jsonify({
            "error":
                "Unauthorized"
        }), 401


    with lock:

        queue_size =
            len(
                pending_commands
            )


    with apps_lock:

        app_count =
            len(
                available_apps
            )


    with screenshots_lock:

        screenshot_count =
            len(
                screenshot_results
            )


    return jsonify({

        "relay":
            "online",

        "queued_commands":
            queue_size,

        "discovered_apps":
            app_count,

        "screenshots":
            screenshot_count

    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print(
        "Laptop Remote Relay starting..."
    )


    print(
        f"Listening on port {PORT}"
    )


    threading.Thread(
        target=
            screenshot_cleanup_loop,

        daemon=True
    ).start()


    app.run(

        host="0.0.0.0",

        port=PORT,

        debug=False

    )
