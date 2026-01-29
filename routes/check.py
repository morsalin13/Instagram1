from flask import Blueprint, request, jsonify
from services.instagram import check_username

check_bp = Blueprint("check", __name__)

@check_bp.route("/check", methods=["POST"])
def check():
    # ---------- VALIDATE JSON ----------
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request must be JSON"
        }), 400

    data = request.get_json(silent=True)
    if not data or "usernames" not in data:
        return jsonify({
            "success": False,
            "error": "Expected body: { usernames: [] }"
        }), 400

    usernames = data.get("usernames")
    if not isinstance(usernames, list):
        return jsonify({
            "success": False,
            "error": "'usernames' must be a list"
        }), 400

    # ---------- PROCESS ----------
    results = []
    seen = set()

    for username in usernames:
        if not username:
            continue

        username = str(username).strip().lower()

        # avoid duplicate checks
        if username in seen:
            continue
        seen.add(username)

        try:
            result = check_username(username)
            results.append(result)
        except Exception as e:
            # NEVER crash the whole request
            results.append({
                "username": username,
                "exists": None,
                "error": str(e),
                "method": "backend-error"
            })

    # ---------- RESPONSE ----------
    return jsonify({
        "success": True,
        "data": results
    }), 200