import os
import requests
import random

# ---------------- CONFIG ----------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

RAPIDAPI_HOST = "instagram-api-fast-reliable-data-scraper.p.rapidapi.com"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 Version/16.5 Mobile Safari/604.1",
]

# ---------------- HEADERS BUILDER ----------------
def build_headers():
    return {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
    }

# ---------------- CORE FUNCTION ----------------
def check_username(username: str):
    url = "https://instagram-api-fast-reliable-data-scraper.p.rapidapi.com/user_profile"
    params = { "username": username }

    try:
        r = requests.get(
            url,
            headers=build_headers(),
            params=params,
            timeout=10
        )

        if r.status_code == 404:
            return {
                "username": username,
                "exists": False,
                "method": "rapidapi"
            }

        if r.status_code != 200:
            return {
                "username": username,
                "exists": None,
                "error": f"HTTP {r.status_code}",
                "method": "rapidapi"
            }

        data = r.json()

        if not data or "data" not in data:
            return {
                "username": username,
                "exists": False,
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