import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "X-IG-App-ID": "936619743392459"  # public web app id
}

def check_username(username: str):
    url = "https://i.instagram.com/api/v1/users/web_profile_info/"
    params = {"username": username}

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)

        if r.status_code == 404:
            return {
                "username": username,
                "exists": False,
                "method": "web_profile_info"
            }

        if r.status_code != 200:
            return {
                "username": username,
                "exists": None,
                "error": f"HTTP {r.status_code}",
                "method": "web_profile_info"
            }

        data = r.json()

        if "data" not in data or "user" not in data["data"]:
            return {
                "username": username,
                "exists": False,
                "method": "web_profile_info"
            }

        user = data["data"]["user"]

        return {
            "username": username,
            "exists": True,
            "uid": user["id"],
            "followers": user["edge_followed_by"]["count"],
            "following": user["edge_follow"]["count"],
            "private": user["is_private"],
            "verified": user["is_verified"],
            "method": "web_profile_info"
        }

    except Exception as e:
        return {
            "username": username,
            "exists": None,
            "error": str(e),
            "method": "web_profile_info"
        }