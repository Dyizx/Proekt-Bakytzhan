import requests
from settings import API_KEY, YOUTUBE_API_KEY


def get_steam_link(game_name: str):
    try:
        search_url = f"https://store.steampowered.com/api/storesearch/?term={requests.utils.quote(game_name)}&l=english&cc=US"
        response = requests.get(search_url, timeout=5)
        data = response.json()
        if data.get("items"):
            app_id = data["items"][0]["id"]
            return f"https://store.steampowered.com/app/{app_id}/"
        return f"https://store.steampowered.com/search/?term={requests.utils.quote(game_name)}"
    except:
        return f"https://store.steampowered.com/search/?term={requests.utils.quote(game_name)}"


def get_youtube_review(game_name: str):
    try:
        url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&q={requests.utils.quote(game_name + ' review')}"
            f"&type=video&maxResults=1&key={YOUTUBE_API_KEY}"
        )
        response = requests.get(url, timeout=5)
        data = response.json()
        items = data.get("items", [])
        if items:
            video_id = items[0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={video_id}"
        return f"https://www.youtube.com/results?search_query={requests.utils.quote(game_name + ' review')}"
    except:
        return f"https://www.youtube.com/results?search_query={requests.utils.quote(game_name + ' review')}"


def fetch_game_data(game_name: str):
    url = f"https://api.rawg.io/api/games?key={API_KEY}&search={game_name}&page_size=5"
    response = requests.get(url)
    data = response.json()

    if not data.get("results"):
        return None

    game = next(
        (r for r in data["results"] if r["name"].lower() == game_name.lower()),
        data["results"][0]
    )

    game_id = game["id"]
    details = requests.get(f"https://api.rawg.io/api/games/{game_id}?key={API_KEY}").json()

    screenshots_data = requests.get(
        f"https://api.rawg.io/api/games/{game_id}/screenshots?key={API_KEY}&page_size=4"
    ).json()
    screenshots = [s["image"] for s in screenshots_data.get("results", [])]

    return game, details, screenshots