# backend/app.py
import os, re, json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()
app = Flask(__name__)

CORS(app, origins=os.getenv("FRONTEND_ORIGIN","*"))

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Client credentials for public playlist access
client_credentials_manager = SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)


def extract_playlist_id(url_or_id: str):
    if not url_or_id:
        return None
    m = re.search(r"(playlist[/:])?([0-9A-Za-z]{22})", url_or_id)
    return m.group(2) if m else None

@app.get("/api/playlist")
def get_playlist_tracks():
    q = (request.args.get("q") or "").strip()
    pid = extract_playlist_id(q)
    if not pid:
        return jsonify({"error": "invalid_playlist"}), 400

    # Only support public playlists using client credentials
    try:
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        playlist_info = sp.playlist(pid)
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return jsonify({"error": "playlist_not_found", "message": "Playlist not found. Please check the playlist URL or ID."}), 404
        return jsonify({"error": "playlist_not_accessible", "message": "This playlist is private or not accessible. Only public playlists are supported."}), 403

    tracks = []
    results = sp.playlist_items(pid, additional_types=("track",), limit=100)
    while results:
        for item in results.get("items", []):
            t = item.get("track") or {}
            if not t: 
                continue
            album_images = (t.get("album") or {}).get("images") or []
            img = album_images[1]["url"] if len(album_images) > 1 else (album_images[0]["url"] if album_images else "")
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            tracks.append({
                "id": t.get("id"),
                "name": t.get("name"),
                "artists": artists,
                "albumArt": img
            })
        if results.get("next"):
            results = sp.next(results)
        else:
            results = None
    
    return jsonify({
        "tracks": tracks,
        "playlist_name": playlist_info.get("name", "Unknown Playlist")
    })

@app.get("/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
