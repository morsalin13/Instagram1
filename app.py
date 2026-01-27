from flask import Flask, render_template, request, jsonify
import instaloader
import requests
import time
import random
import os   # 🔥 এই লাইনটাই missing ছিল (সব সমস্যা এখান থেকে)

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ---------------- CONFIG ----------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0)"
]

# ---------------- INSTALOADER ----------------
L = instaloader.Instaloader()
L.context.max_connection_attempts = 1

# 🔥 SERVER INSTAGRAM LOGIN (Railway ENV variables)
IG_USER = os.getenv("IG_USERNAME")
IG_PASS = os.getenv("IG_PASSWORD")

if IG_USER and IG_PASS:
    try:
        L.login(IG_USER, IG_PASS)
        print("✅ Instagram server account logged in")
    except Exception as e:
        print("❌ Instagram login failed:", e)
else:
    print("⚠️ IG_USERNAME / IG_PASSWORD not found in ENV")

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/check", methods=["POST"])
def check_usernames():
    data = request.get_json()
    usernames = data.get("usernames", [])
    results = []

    for username in usernames:
        username = username.strip()
        if not username:
            continue

        result = check_instaloader(username)
        results.append(result)
        time.sleep(random.uniform(1.2, 2.0))

    return jsonify(results)

# ---------------- CORE CHECK ----------------
def check_instaloader(username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return {
            "username": username,
            "status": "Taken",
            "account_status": "Live",
            "uid": profile.userid,
            "followers": profile.followers,
            "following": profile.followees,
            "method": "Instaloader"
        }

    except instaloader.ProfileNotExistsException:
        return {
            "username": username,
            "status": "Available",
            "details": "This account is not created yet",
            "method": "Instaloader"
        }

    except Exception as e:
        err = str(e)
        if "401" in err or "404" in err or "JSON Query" in err:
            return {
                "username": username,
                "status": "Available",
                "details": "This account is not created yet",
                "method": "Instaloader"
            }

        return {
            "username": username,
            "status": "Error",
            "details": err,
            "method": "Instaloader"
        }
