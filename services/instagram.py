import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-IG-App-ID": "936619743392459",
    "Referer": "https://www.instagram.com/",
}

def check_username(username: str):
    url = "https://i.instagram.com/api/v1/users/web_profile_info/"
    params = {"username": username}

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=10
        )

        if r.status_code == 404:
            return {
                "username": username,
                "exists": False,
                "followers": None,
                "following": None,
                "private": None,
                "verified": None,
                "method": "web_profile_info"
            }

        if r.status_code != 200:
            return {
                "username": username,
                "exists": None,
                "followers": None,
                "following": None,
                "private": None,
                "verified": None,
                "error": f"HTTP {r.status_code}",
                "method": "web_profile_info"
            }

        data = r.json()

        if "data" not in data or "user" not in data["data"]:
            return {
                "username": username,
                "exists": False,
                "followers": None,
                "following": None,
                "private": None,
                "verified": None,
                "method": "web_profile_info"
            }

        user = data["data"]["user"]

        return {
            "username": username,
            "exists": True,
            "uid": user.get("id"),
            "followers": user.get("edge_followed_by", {}).get("count"),
            "following": user.get("edge_follow", {}).get("count"),
            "private": user.get("is_private"),
            "verified": user.get("is_verified"),
            "method": "web_profile_info"
        }

    except Exception as e:
        return {
            "username": username,
            "exists": None,
            "followers": None,
            "following": None,
            "private": None,
            "verified": None,
            "error": "Request failed",
            "method": "web_profile_info"
        }
