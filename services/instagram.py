import os
import requests

# ---------------- CONFIG ----------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

RAPIDAPI_HOST = "instagram-api-fast-reliable-data-scraper.p.rapidapi.com"

# ---------------- HEADERS ----------------
def build_headers():
    return {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "Accept": "application/json",
    }

# ---------------- CORE FUNCTION ----------------
def check_username(username: str):
    url = "https://instagram-api-fast-reliable-data-scraper.p.rapidapi.com/user_profile"
    params = {"username": username}

    try:
        r = requests.get(
            url,
            headers=build_headers(),
            params=params,
            timeout=10
        )

        # Explicit not found
        if r.status_code == 404:
            return {
                "username": username,
                "exists": False,
                "method": "rapidapi"
            }

        # Any non-200 = API / rate / temp issue
        if r.status_code != 200:
            return {
                "username": username,
                "exists": None,
                "error": f"HTTP {r.status_code}",
                "method": "rapidapi"
            }

        data = r.json()

        # IMPORTANT FIX:
        # data missing / null ≠ available
        if not data or "data" not in data or data["data"] is None:
            return {
                "username": username,
                "exists": None,
                "error": "Profile data unavailable (rate limit or temporary block)",
                "method": "rapidapi"
            }

        user = data["data"]

        return {
            "username": username,
            "exists": True,
            "followers": user.get("follower_count"),
            "following": user.get("following_count"),
            "private": user.get("is_private"),
            "verified": user.get("is_verified"),
            "method": "rapidapi"
        }

    except Exception as e:
        return {
            "username": username,
            "exists": None,
            "error": str(e),
            "method": "rapidapi"
        }
