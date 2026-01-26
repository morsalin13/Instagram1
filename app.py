from flask import Flask, render_template, request, jsonify, session
import instaloader
import requests
import time
import os
import random

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # must be set

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

# -------------------------
# Helpers
# -------------------------

def get_user_instaloader():
    """
    Create Instaloader instance for the currently logged-in user.
    """
    if 'ig_username' not in session or 'ig_password' not in session:
        return None

    L = instaloader.Instaloader()
    L.context.max_connection_attempts = 1
    L.login(session['ig_username'], session['ig_password'])
    return L


# -------------------------
# Routes
# -------------------------

@app.route('/')
def index():
    return render_template(
        'index.html',
        logged_in=('ig_username' in session),
        ig_user=session.get('ig_username')
    )


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"})

    try:
        L = instaloader.Instaloader()
        L.context.max_connection_attempts = 1
        L.login(username, password)

        # save only in user session (NOT global, NOT file)
        session['ig_username'] = username
        session['ig_password'] = password

        return jsonify({"success": True, "message": "Logged in successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route('/check', methods=['POST'])
def check():
    # login mandatory
    if 'ig_username' not in session:
        return jsonify({"error": "Login required"}), 401

    usernames = request.json.get('usernames', [])
    results = []

    L = get_user_instaloader()
    if not L:
        return jsonify({"error": "Instagram session error"}), 401

    for username in usernames:
        username = username.strip()
        if not username:
            continue

        # Fast check first
        result = check_username_fast(username)

        # Deep scan if taken / uncertain
        if result['status'] in ['Taken', 'Error', 'Uncertain']:
            deep = check_username_instaloader(L, username)
            if deep['status'] != 'Error':
                result = deep

        results.append(result)
        time.sleep(random.uniform(1.5, 3.0))

    return jsonify(results)


# -------------------------
# Username check logic
# -------------------------

def check_username_fast(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        r = requests.get(url, headers=headers, timeout=5)

        if r.status_code == 404:
            return {"username": username, "status": "Available", "details": "User not found", "method": "Fast"}

        if r.status_code == 200:
            if "Sorry, this page isn't available." in r.text:
                return {"username": username, "status": "Available", "details": "Page not found", "method": "Fast"}

            return {"username": username, "status": "Taken", "details": "Account appears Live", "method": "Fast"}

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
        if "401" in err or "JSON Query" in err:
            return {"username": username, "status": "Available", "details": "Not live / not created", "method": "Instaloader"}

        return {"username": username, "status": "Error", "details": err, "method": "Instaloader"}


# -------------------------
# Run
# -------------------------

if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
