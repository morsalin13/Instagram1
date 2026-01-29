import os
import time
import random
import logging
from flask import Flask, render_template, request, jsonify
import instaloader

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

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
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "details": str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "details": str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal Server Error", "details": str(error)}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if hasattr(e, "code"):
        return jsonify({"error": str(e), "details": str(e)}), e.code
    # Handle non-HTTP exceptions
    logger.error(f"Unhandled Exception: {e}")
    return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

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
            return jsonify({"error": "Invalid Content-Type", "details": "Request body must be JSON"}), 400
        
        data = request.get_json()
        if not data or "usernames" not in data:
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
        logger.error(f"Error in /check: {e}")
        return jsonify({"error": "Processing Error", "details": str(e)}), 500

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
    app.run(debug=True)
