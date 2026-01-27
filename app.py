from flask import Flask, render_template, request, jsonify
import instaloader
import requests
import time
import os
import random

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ================= CONFIG =================
SESSION_FILE_PREFIX = "session-"
is_logged_in = False

ADMIN_USERNAME = os.environ.get("ADMIN_IG_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_IG_PASSWORD")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
]

# ================= INSTALOADER =================
L = instaloader.Instaloader()
L.context.max_connection_attempts = 1


def auto_admin_login():
    """Auto login using admin Instagram credentials from env"""
    global is_logged_in, L

    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        print("❌ Admin IG credentials not set")
        return

    session_file = f"{SESSION_FILE_PREFIX}{ADMIN_USERNAME}"

    try:
        if os.path.exists(session_file):
            L.load_session_from_file(ADMIN_USERNAME, filename=session_file)
            is_logged_in = True
            print("✅ Admin session loaded")
        else:
            L.login(ADMIN_USERNAME, ADMIN_PASSWORD)
            L.save_session_to_file(session_file)
            is_logged_in = True
            print("✅ Admin auto-login successful")

    except Exception as e:
        is_logged_in = False
        print("❌ Admin login failed:", e)


# Auto login on startup
auto_admin_login()

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html", logged_in=True)


@app.route("/login", methods=["POST"])
def login():
    # User login DISABLED
    return jsonify({
        "success": False,
        "message": "Instagram login is disabled. This site uses a secured internal session."
    })


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


# ================= CHECK METHODS =================
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
        return {
            "username": username,
            "status": "Error",
            "details": str(e),
            "method": "Fast"
        }


def check_instaloader(username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return {
            "username": username,
            "status": "Taken",
            "uid": profile.userid,
            "followers": profile.followers,
            "account_status": "Live",
            "method": "Instaloader",
        }

    except instaloader.ProfileNotExistsException:
        return {
            "username": username,
            "status": "Available",
            "method": "Instaloader"
        }

    except instaloader.LoginRequiredException:
        return {
            "username": username,
            "status": "Error",
            "details": "Login required",
            "method": "Instaloader"
        }

    except Exception as e:
        err = str(e)
        if "401" in err or "JSON Query" in err:
            return {
                "username": username,
                "status": "Available",
                "method": "Instaloader"
            }

        return {
            "username": username,
            "status": "Error",
            "details": err,
            "method": "Instaloader"
        }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))