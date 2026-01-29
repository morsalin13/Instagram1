import time
import random
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import HTTPException
import instaloader

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["TRAP_HTTP_EXCEPTIONS"] = True

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- INSTALOADER (NO LOGIN) ----------------
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    save_metadata=False,
    compress_json=False,
)

# IMPORTANT: no login, no session
L.context.max_connection_attempts = 1
logger.info("ℹ️ Instaloader initialized (NO LOGIN mode)")

# ---------------- ERROR HANDLER ----------------
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled Exception: {e}", exc_info=True)

    if isinstance(e, HTTPException):
        return jsonify({
            "success": False,
            "error": e.name,
            "details": e.description
        }), e.code

    return jsonify({
        "success": False,
        "error": "Internal Server Error",
        "details": str(e)
    }), 500

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"ok": True})

@app.route("/check", methods=["POST"])
def check_usernames():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Invalid Content-Type",
            "details": "Request must be JSON"
        }), 400

    data = request.get_json(silent=True)
    if not data or "usernames" not in data:
        return jsonify({
            "success": False,
            "error": "Missing usernames",
            "details": "Expected { usernames: [] }"
        }), 400

    usernames = data.get("usernames")
    if not isinstance(usernames, list):
        return jsonify({
            "success": False,
            "error": "Invalid format",
            "details": "'usernames' must be a list"
        }), 400

    results = []
    for username in usernames:
        username = str(username).strip()
        if not username:
            continue

        results.append(check_instagram_public(username))
        time.sleep(random.uniform(0.8, 1.5))  # soft delay

    return jsonify({
        "success": True,
        "data": results
    })

# ---------------- CORE LOGIC (NO LOGIN) ----------------
def check_instagram_public(username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)

        return {
            "username": username,
            "exists": True,
            "uid": profile.userid,
            "followers": profile.followers,
            "following": profile.followees,
            "private": profile.is_private,
            "verified": profile.is_verified,
            "method": "instaloader-public"
        }

    except instaloader.ProfileNotExistsException:
        return {
            "username": username,
            "exists": False,
            "details": "Username not found",
            "method": "instaloader-public"
        }

    except Exception as e:
        return {
            "username": username,
            "exists": None,
            "error": str(e),
            "method": "instaloader-public"
        }

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)