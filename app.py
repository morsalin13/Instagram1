from flask import Flask, render_template, request, jsonify
import instaloader
import time
import random
import os

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ---------------- INSTALOADER ----------------
L = instaloader.Instaloader()
L.context.max_connection_attempts = 1
LOGGED_IN = False

# ---------------- LOGIN FUNCTION (SAFE) ----------------
def login_instagram():
    global LOGGED_IN
    if LOGGED_IN:
        return

    IG_USER = os.getenv("IG_USERNAME")
    IG_PASS = os.getenv("IG_PASSWORD")

    if not IG_USER or not IG_PASS:
        print("⚠️ IG credentials missing")
        return

    try:
        L.login(IG_USER, IG_PASS)
        LOGGED_IN = True
        print("✅ Instagram server account logged in")
    except Exception as e:
        print("❌ Instagram login failed:", e)

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html", logged_in=True)

@app.route("/check", methods=["POST"])
def check_usernames():
    login_instagram()  # 🔥 login only when needed

    usernames = request.json.get("usernames", [])
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
