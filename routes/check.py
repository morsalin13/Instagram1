from flask import Blueprint, request, jsonify
from services.instagram import check_username

check_bp = Blueprint("check", __name__)

@check_bp.route("/check", methods=["POST"])
def check():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request must be JSON"
        }), 400

    data = request.get_json(silent=True)
    if not data or "usernames" not in data:
        return jsonify({
            "success": False,
            "error": "Expected { usernames: [] }"
        }), 400

    usernames = data.get("usernames")
    if not isinstance(usernames, list):
        return jsonify({
            "success": False,
            "error": "'usernames' must be a list"
        }), 400

    results = []
    for username in usernames:
        username = str(username).strip()
        if not username:
            continue

        results.append(check_username(username))

    return jsonify({
        "success": True,
        "data": results
    })