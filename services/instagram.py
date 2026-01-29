import requests
import re
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9"
}

def check_username(username: str):
    url = f"https://www.instagram.com/{username}/"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)

        if r.status_code == 404:
            return {
                "username": username,
                "exists": False,
                "method": "public-scraping"
            }

        if r.status_code != 200:
            return {
                "username": username,
                "exists": None,
                "error": f"HTTP {r.status_code}",
                "method": "public-scraping"
            }

        # Extract shared data JSON
        match = re.search(
            r"window\._sharedData\s*=\s*(\{.*?\});",
            r.text
        )

        if not match:
            return {
                "username": username,
                "exists": None,
                "error": "Profile data not found",
                "method": "public-scraping"
            }

        data = json.loads(match.group(1))
        user = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]

        return {
            "username": username,
            "exists": True,
            "uid": user["id"],
            "followers": user["edge_followed_by"]["count"],
            "following": user["edge_follow"]["count"],
            "private": user["is_private"],
            "verified": user["is_verified"],
            "method": "public-scraping"
        }

    except Exception as e:
        return {
            "username": username,
            "exists": None,
            "error": str(e),
            "method": "public-scraping"
        }