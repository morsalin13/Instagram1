import os
import time
import random
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import HTTPException
import instaloader

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
# TRAP_HTTP_EXCEPTIONS ensures that all HTTP errors (including 500s) are handled by the custom error handler
app.config['TRAP_HTTP_EXCEPTIONS'] = True

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- CONFIG ----------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0)"
]

# ---------------- INSTALOADER ----------------
L = instaloader.Instaloader()
L.context.max_connection_attempts = 1

# IG LOGIN (Railway ENV variables)
IG_USER = os.getenv("IG_USERNAME")
IG_PASS = os.getenv("IG_PASSWORD")

if IG_USER and IG_PASS:
    try:
        L.login(IG_USER, IG_PASS)
        logger.info("✅ Instagram server account logged in")
    except Exception as e:
        logger.error(f"❌ Instagram login failed: {e}")
else:
    logger.warning("⚠️ IG_USERNAME / IG_PASSWORD not found in ENV")

# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(Exception)
def handle_exception(e):
    # Log the full error
    logger.error(f"Unhandled Exception: {e}", exc_info=True)
    
    # Return JSON for all API requests
    # Check if request accepts JSON or is an API route
    if request.path.startswith("/check") or request.path.startswith("/health") or request.is_json:
        if isinstance(e, HTTPException):
            return jsonify({
                "error": e.name,
                "details": e.description,
                "code": e.code
            }), e.code
            
        return jsonify({
            "error": "Internal Server Error",
            "details": str(e)
        }), 500
        
    # Default to original handling for non-API routes (e.g. 404 on a page)
    return e

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"ok": True})

@app.route("/check", methods=["POST"])
def check_usernames():
    try:
        if not request.is_json:
            # Try to force parse if possible, or fail
            return jsonify({"error": "Invalid Content-Type", "details": "Request body must be JSON"}), 400
        
        data = request.get_json(silent=True) # silent=True returns None instead of crashing
        if data is None:
             return jsonify({"error": "Invalid JSON", "details": "Could not parse JSON body"}), 400

        if "usernames" not in data:
             return jsonify({"error": "Missing 'usernames' field", "details": "Please provide a list of usernames"}), 400
             
        usernames = data.get("usernames")
        if not isinstance(usernames, list):
            return jsonify({"error": "Invalid format", "details": "'usernames' must be a list"}), 400

        results = []
        for username in usernames:
            username = str(username).strip()
            if not username:
                continue

            result = check_instaloader(username)
            results.append(result)
            time.sleep(random.uniform(1.2, 2.0))

        return jsonify(results)

    except Exception as e:
        logger.error(f"Error in /check: {e}", exc_info=True)
        return jsonify({"error": "Processing Error", "details": str(e)}), 500

# ---------------- CORE CHECK ----------------
def check_instaloader(username):
    try:
        # Check if L is valid
        if not L:
             raise Exception("Instaloader instance not initialized")

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
        # Handle specific Instaloader errors if needed, or generic ones
        if "401" in err or "404" in err or "JSON Query" in err:
             return {
                "username": username,
                "status": "Available",
                "details": "This account is not created yet (inferred from error)",
                "method": "Instaloader"
            }
        
        return {
            "username": username,
            "status": "Error",
            "details": err,
            "method": "Instaloader"
        }

if __name__ == "__main__":
    # DISABLE DEBUG MODE to prevent HTML error pages
    app.run(debug=False, port=5000)
