from flask import Flask, Response, request
import os
import requests
import base64

app = Flask(__name__)

# 获取环境变量 (自动兼容两种写法)
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_SECRET_ID") or os.getenv("SPOTIFY_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

def get_access_token():
    if not REFRESH_TOKEN:
        return None
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    try:
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN},
            headers={"Authorization": f"Basic {auth_b64}"},
            timeout=10
        )
        return response.json().get("access_token")
    except:
        return None

def get_now_playing():
    token = get_access_token()
    if not token: return None
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # 1. 尝试获取正在播放
        resp = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers, timeout=10)
        if resp.status_code == 200: return resp.json().get("item")
        # 2. 获取最近播放
        resp = requests.get("https://api.spotify.com/v1/me/player/recently-played?limit=1", headers=headers, timeout=10)
        if resp.status_code == 200 and resp.json().get("items"): return resp.json()["items"][0]["track"]
    except: pass
    return None

@app.route("/", defaults={'path': ''})
@app.route("/<path:path>")
def catch_all(path):
    item = get_now_playing()
    # 默认值
    track_name, artist_name, cover_data = "Not Playing", "Spotify", ""
    is_playing = False

    if item:
        is_playing = True
        track_name = item.get("name", "Unknown").replace("&", "&")
        artist_name = item["artists"][0]["name"].replace("&", "&") if item["artists"] else "Unknown"
        if item.get("album") and item["album"].get("images"):
            try:
                img_resp = requests.get(item["album"]["images"][0]["url"], timeout=5)
                if img_resp.status_code == 200:
                    cover_data = base64.b64encode(img_resp.content).decode()
            except: pass

    # 生成图片
    img_tag = f'<image href="data:image/jpeg;base64,{cover_data}" x="10" y="10" height="80" width="80" rx="4"/>' if cover_data else '<rect x="10" y="10" width="80" height="80" fill="#333" rx="4"/>'
    bars = ""
    if is_playing:
        for i in range(12):
            h = 10 + (i * 5 % 20)
            bars += f'<rect x="{300 + i*6}" y="{50-h}" width="4" height="{h}" fill="#1DB954"><animate attributeName="height" values="{h};25;{h}" dur="0.8s" repeatCount="indefinite"/></rect>'

    svg = f"""<svg width="400" height="100" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="#121212" rx="10"/>
      {img_tag}
      <text x="100" y="45" fill="white" font-family="Arial" font-weight="bold" font-size="14">{track_name}</text>
      <text x="100" y="70" fill="#b3b3b3" font-family="Arial" font-size="12">{artist_name}</text>
      {bars}
    </svg>"""
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})
