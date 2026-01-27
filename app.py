from flask import Flask, render_template, request, jsonify
import instaloader
import requests
import time
import random
import os

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ---------------- CONFIG ----------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
]

# ---------------- INSTALOADER ----------------
L = instaloader.Instaloader()
L.context.max_connection_attempts = 1
is_logged_in = False

SESSION_FILE = "session-server"

def load_server_session():
    global is_logged_in
    try:
        if os.path.exists(SESSION_FILE):
            L.load_session_from_file(
                os.environ.get("IG_USERNAME"),
                filename=SESSION_FILE
            )
            is_logged_in = True
    except:
        is_logged_in = False

# login once using ENV (Railway Variables)
def login_with_env():
    global is_logged_in
    try:
        ig_user = os.environ.get("IG_USERNAME")
        ig_pass = os.environ.get("IG_PASSWORD")

        if ig_user and ig_pass:
            L.login(ig_user, ig_pass)
            L.save_session_to_file(filename=SESSION_FILE)
            is_logged_in = True
    except:
        is_logged_in = False

load_server_session()
if not is_logged_in:
    login_with_env()

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html", logged_in=is_logged_in)

@app.route("/check", methods=["POST"])
def check_usernames():
    usernames = request.json.get("usernames", [])
    results = []

    for username in usernames:
        username = username.strip()
        if not username:
            continue

        fast = check_fast(username)

        if fast["status"] == "Taken" and is_logged_in:
            deep = check_instaloader(username)
            results.append(deep)
        else:
            results.append(fast)

        time.sleep(random.uniform(1.0, 2.0))

    return jsonify(results)

# ---------------- FAST CHECK ----------------
def check_fast(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        r = requests.get(url, headers=headers, timeout=6, allow_redirects=True)

        if r.status_code == 404:
            return {
                "username": username,
                "status": "Available",
                "details": "not created yet",
                "method": "Fast"
            }

        if "Sorry, this page isn't available." in r.text:
            return {
                "username": username,
                "status": "Available",
                "details": "not created yet",
                "method": "Fast"
            }

        if '"profilePage_' in r.text or '"username":"' in r.text:
            return {
                "username": username,
                "status": "Taken",
                "details": "account exists",
                "method": "Fast"
            }

        return {
            "username": username,
            "status": "Available",
            "details": "not created yet",
            "method": "Fast"
        }

    except Exception as e:
        return {
            "username": username,
            "status": "Error",
            "details": str(e),
            "method": "Fast"
        }

# ---------------- INSTALOADER DEEP CHECK ----------------
def check_instaloader(username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)

        return {
            "username": username,
            "status": "Taken",
            "uid": profile.userid,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "account_status": "Live",
            "method": "Instaloader"
        }

    except instaloader.ProfileNotExistsException:
        return {
            "username": username,
            "status": "Available",
            "details": "not created yet",
            "method": "Instaloader"
        }

    except Exception as e:
        return {
            "username": username,
            "status": "Error",
            "details": str(e),
            "method": "Instaloader"
        }
