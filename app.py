from flask import Flask, render_template, request, jsonify
import instaloader
import requests
import time
import os
import random

app = Flask(__name__)

# Instaloader (anonymous only for public safety)
L = instaloader.Instaloader()
L.context.max_connection_attempts = 1

# PUBLIC MODE ONLY
is_logged_in = False  # always false on public site

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

@app.route('/')
def index():
    return render_template('index.html', logged_in=False)

# 🔒 LOGIN DISABLED ON PUBLIC VERSION
@app.route('/login', methods=['POST'])
def login():
    return jsonify({
        "success": False,
        "message": "Instagram login is disabled on the public version."
    })

@app.route('/check', methods=['POST'])
def check():
    usernames = request.json.get('usernames', [])
    results = []

    for username in usernames:
        username = username.strip()
        if not username:
            continue

        # Fast check (main method)
        result = check_username_fast(username)

        # Anonymous instaloader fallback only if fast check errors
        if result['status'] == 'Error':
            insta_result = check_username_instaloader(username)
            if insta_result['status'] != 'Error':
                result = insta_result

        results.append(result)

        time.sleep(random.uniform(0.5, 1.5))

    return jsonify(results)

def check_username_fast(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 404:
            return {
                "username": username,
                "status": "Available",
                "details": "User not found (404)",
                "method": "Fast"
            }

        if response.status_code == 200:
            text = response.text

            if "Sorry, this page isn't available." in text:
                return {
                    "username": username,
                    "status": "Available",
                    "details": "Page content indicates not found",
                    "method": "Fast"
                }

            if f"@{username}" in text or f"{username})" in text:
                return {
                    "username": username,
                    "status": "Taken",
                    "details": "Account is Live (Found in Page)",
                    "method": "Fast"
                }

            return {
                "username": username,
                "status": "Taken",
                "details": "Account appears Live",
                "method": "Fast"
            }

        return {
            "username": username,
            "status": "Error",
            "details": f"Status {response.status_code}",
            "method": "Fast"
        }

    except Exception as e:
        return {
            "username": username,
            "status": "Error",
            "details": str(e),
            "method": "Fast"
        }

def check_username_instaloader(username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return {
            "username": username,
            "status": "Taken",
            "details": f"Live | Followers: {profile.followers}",
            "followers": profile.followers,
            "uid": profile.userid,
            "account_status": "Live",
            "method": "Instaloader"
        }

    except instaloader.ProfileNotExistsException:
        return {
            "username": username,
            "status": "Available",
            "details": "User not found",
            "method": "Instaloader"
        }

    except Exception as e:
        err = str(e)
        if "401" in err or "JSON Query" in err or "404" in err:
            return {
                "username": username,
                "status": "Available",
                "details": "(this account is not live or not created yet)",
                "method": "Instaloader"
            }

        return {
            "username": username,
            "status": "Error",
            "details": err,
            "method": "Instaloader"
        }

if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
