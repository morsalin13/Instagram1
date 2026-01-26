from flask import Flask, render_template, request, jsonify, session
import instaloader
import requests
import time
import os
import random
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key")

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

def _sid():
    """Ensure a stable session id for storing cookies on server."""
    if "sid" not in session:
        session["sid"] = secrets.token_urlsafe(16)
    return session["sid"]

def _cookie_file():
    return f"/tmp/ig_cookies_{_sid()}.txt"

def is_connected():
    return os.path.exists(_cookie_file()) and os.path.getsize(_cookie_file()) > 0

def parse_cookie_header(cookie_text: str) -> dict:
    """
    Accepts:
      - "key=value; key2=value2; ..."
    Returns dict {key: value}
    """
    cookies = {}
    for part in cookie_text.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        cookies[k.strip()] = v.strip()
    return cookies

def get_instaloader_from_saved_cookies():
    """Create Instaloader using cookies saved for THIS visitor only."""
    if not is_connected():
        return None

    with open(_cookie_file(), "r", encoding="utf-8") as f:
        cookie_text = f.read().strip()

    cookies = parse_cookie_header(cookie_text)
    if not cookies:
        return None

    L = instaloader.Instaloader()
    L.context.max_connection_attempts = 1

    # Put cookies into Instaloader's requests session
    for k, v in cookies.items():
        L.context._session.cookies.set(k, v)

    return L

@app.route("/")
def index():
    return render_template("index.html", connected=is_connected())

@app.route("/connect_cookies", methods=["POST"])
def connect_cookies():
    cookie_text = (request.json.get("cookie_text") or "").strip()
    if not cookie_text:
        return jsonify({"success": False, "message": "Cookie text is required."})

    # Save cookies for this visitor
    os.makedirs("/tmp", exist_ok=True)
    with open(_cookie_file(), "w", encoding="utf-8") as f:
        f.write(cookie_text)

    # Validate login
    try:
        L = get_instaloader_from_saved_cookies()
        if not L:
            return jsonify({"success": False, "message": "Invalid cookie format."})

        # Instaloader test_login returns username or None
        who = L.context.test_login()
        if not who:
            # Not logged in -> remove
            try:
                os.remove(_cookie_file())
            except:
                pass
            return jsonify({
                "success": False,
                "message": "Not logged in. Please login on Instagram in your browser, then paste cookies again."
            })

        return jsonify({"success": True, "message": f"Connected as {who}."})

    except Exception as e:
        try:
            os.remove(_cookie_file())
        except:
            pass
        return jsonify({"success": False, "message": str(e)})

@app.route("/disconnect", methods=["POST"])
def disconnect():
    try:
        if os.path.exists(_cookie_file()):
            os.remove(_cookie_file())
    except:
        pass
    session.pop("sid", None)
    return jsonify({"success": True})

@app.route("/check", methods=["POST"])
def check():
    if not is_connected():
        return jsonify({"error": "Not connected. Login on Instagram and connect cookies first."}), 401

    usernames = request.json.get("usernames", [])
    results = []

    L = get_instaloader_from_saved_cookies()
    if not L:
        return jsonify({"error": "Session error. Reconnect cookies."}), 401

    for username in usernames:
        username = (username or "").strip()
        if not username:
            continue

        # Fast check first
        fast = check_username_fast(username)
        result = fast

        # If taken/uncertain/error -> deep scan to show uid/followers
        if result["status"] in ["Taken", "Uncertain", "Error"]:
            deep = check_username_instaloader(L, username)

            # Prefer deep if it gives strong result
            if deep["status"] in ["Taken", "Available"]:
                result = deep
            else:
                # keep fast fallback
                result = fast

        results.append(result)

        # Small delay to reduce rate-limit
        time.sleep(random.uniform(1.2, 2.6))

    return jsonify(results)

def check_username_fast(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        r = requests.get(url, headers=headers, timeout=6)

        if r.status_code == 404:
            return {"username": username, "status": "Available", "details": "User not found (404)", "method": "Fast"}

        if r.status_code == 200:
            txt = r.text
            if "Sorry, this page isn't available." in txt:
                return {"username": username, "status": "Available", "details": "Page says not available", "method": "Fast"}
            # Most times 200 means taken
            return {"username": username, "status": "Taken", "details": "Account appears Live", "method": "Fast"}

        if r.status_code in (301, 302):
            return {"username": username, "status": "Uncertain", "details": "Redirected", "method": "Fast"}

        return {"username": username, "status": "Error", "details": f"HTTP {r.status_code}", "method": "Fast"}

    except Exception as e:
        return {"username": username, "status": "Error", "details": str(e), "method": "Fast"}

def check_username_instaloader(L, username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return {
            "username": username,
            "status": "Taken",
            "details": "Live",
            "followers": profile.followers,
            "uid": profile.userid,
            "account_status": "Live",
            "method": "Instaloader"
        }

    except instaloader.ProfileNotExistsException:
        return {"username": username, "status": "Available", "details": "User not found", "method": "Instaloader"}

    except Exception as e:
        err = str(e)
        # If cookies expired / logged out
        if "login" in err.lower() or "LoginRequired" in err:
            return {"username": username, "status": "Error", "details": "Login required (reconnect cookies)", "method": "Instaloader"}
        # Your old behavior: treat JSON Query/401 as available
        if "401" in err or "JSON Query" in err:
            return {"username": username, "status": "Available", "details": "(not live / not created yet)", "method": "Instaloader"}

        return {"username": username, "status": "Error", "details": err, "method": "Instaloader"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
