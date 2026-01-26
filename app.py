from flask import Flask, render_template, request, jsonify
import instaloader
import requests
import time
import os
import random

app = Flask(__name__)

# Global Instaloader instance
L = instaloader.Instaloader()
L.context.max_connection_attempts = 1
is_logged_in = False
SESSION_FILE_PREFIX = "session-"
LAST_USER_FILE = "last_user.txt"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

def load_saved_session():
    global L, is_logged_in
    if os.path.exists(LAST_USER_FILE):
        try:
            with open(LAST_USER_FILE, 'r') as f:
                username = f.read().strip()
            
            if username:
                session_file = f"{SESSION_FILE_PREFIX}{username}"
                if os.path.exists(session_file):
                    print(f"Loading session for {username}...")
                    L.load_session_from_file(username, filename=session_file)
                    is_logged_in = True
                    print("Session loaded successfully.")
        except Exception as e:
            print(f"Failed to load session: {e}")
            is_logged_in = False

# Try to load session on startup
load_saved_session()

@app.route('/')
def index():
    return render_template('index.html', logged_in=is_logged_in)

@app.route('/login', methods=['POST'])
def login():
    global is_logged_in
    global L
    
    username = request.json.get('username')
    password = request.json.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"})
    
    try:
        new_L = instaloader.Instaloader()
        new_L.context.max_connection_attempts = 1
        new_L.login(username, password)
        
        # Save session
        session_file = f"{SESSION_FILE_PREFIX}{username}"
        new_L.save_session_to_file(filename=session_file)
        
        # Save last username
        with open(LAST_USER_FILE, 'w') as f:
            f.write(username)
        
        L = new_L
        is_logged_in = True
        return jsonify({"success": True, "message": "Logged in successfully and session saved."})
    except Exception as e:
        is_logged_in = False
        return jsonify({"success": False, "message": str(e)})

@app.route('/check', methods=['POST'])
def check():
    usernames = request.json.get('usernames', [])
    results = []
    
    for username in usernames:
        username = username.strip()
        if not username:
            continue
            
        # Try fast method first
        fast_result = check_username_fast(username)
        result = fast_result
        
        # If fast method is uncertain, or reports Taken (and we want details), and we are logged in, try instaloader
        if (result['status'] == 'Error' or result['status'] == 'Uncertain' or result['status'] == 'Taken') and is_logged_in:
             insta_result = check_username_instaloader(username)
             
             # If Instaloader succeeds (Taken with details), use it
             if insta_result['status'] == 'Taken':
                 result = insta_result
             # If Instaloader says Available (could be 404 or 401 mapped to Available), use it
             # Note: User wants 401 errors to be treated as Available
             elif insta_result['status'] == 'Available':
                 result = insta_result
             # If Instaloader errors (e.g. LoginRequired), but Fast check was Taken,
             # we prefer to show "Taken" (from Fast) rather than "Error"
             elif insta_result['status'] == 'Error' and fast_result['status'] == 'Taken':
                 result = fast_result
                 result['details'] += " (Deep check failed, some details hidden)"
             # Otherwise (e.g. Fast was Error, Insta was Error), use Insta result or keep Fast result
             else:
                 result = insta_result
        
        # If fast method failed and we are NOT logged in, we can't do much else
        # but we can try instaloader anonymously (might fail)
        elif result['status'] == 'Error' and not is_logged_in:
             # Try instaloader anonymously as a backup
             result = check_username_instaloader(username)

        results.append(result)
        
        # Shorter sleep for fast method, longer if we used instaloader
        if "Instaloader" in result.get('method', ''):
             time.sleep(random.uniform(2, 4))
        else:
             time.sleep(random.uniform(0.5, 1.5))
            
    return jsonify(results)

def check_username_fast(username):
    """
    Checks username availability using standard HTTP requests.
    Much faster and less likely to be rate-limited than API calls.
    """
    url = f"https://www.instagram.com/{username}/"
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 404:
            return {"username": username, "status": "Available", "details": "User not found (404)", "method": "Fast"}
            
        if response.status_code == 200:
            text = response.text
            # Check for common "not found" indicators in the HTML
            if "Sorry, this page isn't available." in text:
                return {"username": username, "status": "Available", "details": "Page content indicates not found", "method": "Fast"}
            
            # If we see the username in the title, it's likely taken
            if f"@{username}" in text or f"{username})" in text:
                 return {"username": username, "status": "Taken", "details": "Account is Live (Found in Page)", "method": "Fast"}
            
            # If we are redirected to login or it's ambiguous
            if "Login" in text and "Instagram" in text:
                return {"username": username, "status": "Uncertain", "details": "Redirected to Login", "method": "Fast"}
                
            # Default to Taken if 200 OK and no error text
            return {"username": username, "status": "Taken", "details": "Account appears Live", "method": "Fast"}
            
        return {"username": username, "status": "Error", "details": f"Status {response.status_code}", "method": "Fast"}
        
    except Exception as e:
        return {"username": username, "status": "Error", "details": str(e), "method": "Fast"}

def check_username_instaloader(username):
    """
    Checks username using Instaloader (API).
    More accurate but slower and stricter rate limits.
    """
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return {
            "username": username,
            "status": "Taken",
            "details": f"Live | Followers: {profile.followers}",
            "uid": profile.userid,
            "followers": profile.followers,
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
    except instaloader.LoginRequiredException:
         return {
            "username": username,
            "status": "Error",
            "details": "Login Required",
            "method": "Instaloader"
        }
    except Exception as e:
        err_str = str(e)
        # Handle 404
        if "404" in err_str:
             return {"username": username, "status": "Available", "details": "User not found", "method": "Instaloader"}
        
        # Handle 401/Unauthorized/JSON Query error as "Available" per user request
        if "401" in err_str or "JSON Query" in err_str:
             return {
                 "username": username, 
                 "status": "Available", 
                 "details": "(this account is not live or not created yet)", 
                 "method": "Instaloader"
             }
             
        return {
            "username": username,
            "status": "Error",
            "details": str(e),
            "method": "Instaloader"
        }

if __name__ == '__main__':
    app.run(debug=True)
