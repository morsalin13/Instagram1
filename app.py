from flask import Flask, render_template, request, jsonify
import instaloader
import requests
import time
import os
import random

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ---------- CONFIG ----------
SESSION_FILE_PREFIX = "session-"
LAST_USER_FILE = "last_user.txt"
is_logged_in = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
]

# ---------- INSTALOADER ----------
L = instaloader.Instaloader()
L.context.max_connection_attempts = 1


def load_saved_session():
    global is_logged_in, L
    if os.path.exists(LAST_USER_FILE):
        try:
            with open(LAST_USER_FILE, "r") as f:
                username = f.read().strip()

            session_file = f"{SESSION_FILE_PREFIX}{username}"
            if username and os.path.exists(session_file):
                L.load_session_from_file(username, filename=session_file)
                is_logged_in = True
        except:
            is_logged_in = False


load_saved_session()

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html", logged_in=is_logged_in)


@app.route("/login", methods=["POST"])
def login():
    global is_logged_in, L

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Username & password required"})

    try:
        new_L = instaloader.Instaloader()
        new_L.context.max_connection_attempts = 1
        new_L.login(username, password)

        session_file = f"{SESSION_FILE_PREFIX}{username}"
        new_L.save_session_to_file(filename=session_file)

        with open(LAST_USER_FILE, "w") as f:
            f.write(username)

        L = new_L
        is_logged_in = True
        return jsonify({"success": True})

    except Exception as e:
        is_logged_in = False
        return jsonify({"success": False, "message": str(e)})


@app.route("/check", methods=["POST"])
def check_usernames():
    usernames = request.json.get("usernames", [])
    results = []

    for username in usernames:
        username = username.strip()
        if not username:
            continue

        result = check_fast(username)

        if is_logged_in and result["status"] in ["Taken", "Uncertain", "Error"]:
            deep = check_instaloader(username)
            if deep["status"] != "Error":
                result = deep

        results.append(result)
        time.sleep(random.uniform(0.8, 1.5))

    return jsonify(results)


# ---------- CHECK METHODS ----------
def check_fast(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        r = requests.get(url, headers=headers, timeout=5)

        if r.status_code == 404:
            return {"username": username, "status": "Available", "method": "Fast"}

        if r.status_code == 200:
            if "Sorry, this page isn't available." in r.text:
                return {"username": username, "status": "Available", "method": "Fast"}
            return {"username": username, "status": "Taken", "method": "Fast"}

        return {"username": username, "status": "Uncertain", "method": "Fast"}

    except Exception as e:
        return {"username": username, "status": "Error", "details": str(e), "method": "Fast"}


def check_instaloader(username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)

        return {
            "username": username,
            "status": "Taken",
            "uid": profile.userid,
            "followers": profile.followers,
            "following": profile.followees,   # ✅ NEW
            "account_status": "Live",
            "method": "Instaloader",
        }

    except instaloader.ProfileNotExistsException:
        return {"username": username, "status": "Available", "method": "Instaloader"}

    except instaloader.LoginRequiredException:
        return {"username": username, "status": "Error", "details": "Login required"}

    except Exception as e:
        err = str(e)
        if "401" in err or "JSON Query" in err:
            return {"username": username, "status": "Available", "method": "Instaloader"}

        return {"username": username, "status": "Error", "details": err, "method": "Instaloader"}
