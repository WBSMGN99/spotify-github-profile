from flask import Flask, Response
import os
import requests
import base64

app = Flask(__name__)

# 自动适配 Kittinan 版的特殊变量名，也兼容标准写法
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_SECRET_ID") or os.getenv("SPOTIFY_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

def get_access_token():
    if not REFRESH_TOKEN:
        print("Error: No Refresh Token")
        return None
        
    # 拼接认证字符串
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
    except Exception as e:
        print(f"Token Error: {e}")
        return None

def get_now_playing_data():
    token = get_access_token()
    if not token: return None
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # 1. 尝试获取正在播放
        resp = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("item")
            
        # 2. 如果没播放，获取最近播放
        resp = requests.get("https://api.spotify.com/v1/me/player/recently-played?limit=1", headers=headers, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items")
            if items: return items[0].get("track")
    except Exception as e:
        print(f"API Error: {e}")
    return None

@app.route("/", defaults={'path': ''})
@app.route("/<path:path>")
def index(path):
    item = get_now_playing_data()
    
    # 默认显示内容
    track_name = "Not Playing"
    artist_name = "Spotify"
    cover_data = ""
    is_playing = False

    if item:
        is_playing = True
        # 处理特殊字符
        track_name = item.get("name", "Unknown").replace("&", "&amp;")
        artists = item.get("artists", [])
        if artists:
            artist_name = artists[0]["name"].replace("&", "&amp;")
        
        # 获取封面并转为 base64
        if item.get("album") and item["album"].get("images"):
            try:
                cover_url = item["album"]["images"][0]["url"]
                img_resp = requests.get(cover_url, timeout=5)
                if img_resp.status_code == 200:
                    cover_data = base64.b64encode(img_resp.content).decode()
            except: pass

    # 生成图片 (如果有封面显示封面，没有显示灰块)
    img_tag = f'<image href="data:image/jpeg;base64,{cover_data}" x="2" y="2" height="60" width="60" rx="4"/>' if cover_data else '<rect x="2" y="2" width="60" height="60" fill="#333" rx="4"/>'
    
    # 简单的动画条
    bars_html = ""
    if is_playing:
        for i in range(15):
            left = 75 + (i * 6)
            anim = 400 + (i * 50 % 200)
            bars_html += f'<rect class="bar" x="{left}" y="45" width="4" height="10" fill="#53b14f" style="animation-duration:{anim}ms"/>'

    css = """<style>.bar { animation: sound 0ms -800ms linear infinite alternate; } @keyframes sound { 0% { height: 3px; opacity: .35; } 100% { height: 16px; opacity: 1; } }</style>"""

    svg = f"""
    <svg width="400" height="64" xmlns="http://www.w3.org/2000/svg">
      <foreignObject width="400" height="64">
        <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Circular,Helvetica,Arial,sans-serif;"></div>
      </foreignObject>
      <rect x="0" y="0" width="400" height="64" fill="#121212" rx="5"/>
      {img_tag}
      <text x="75" y="25" fill="white" font-family="Arial, sans-serif" font-weight="bold" font-size="14">{track_name}</text>
      <text x="75" y="42" fill="#b3b3b3" font-family="Arial, sans-serif" font-size="12">{artist_name}</text>
      {css}
      <g transform="scale(1, -1) translate(0, -60)">{bars_html}</g>
    </svg>
    """
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})
