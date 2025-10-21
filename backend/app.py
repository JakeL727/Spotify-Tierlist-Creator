# backend/app.py
import os, re, json
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from models import SessionLocal, init_db, TierSave

load_dotenv()
app = Flask(__name__)
CORS(app, origins=os.getenv("FRONTEND_ORIGIN","*"))
init_db()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:5000/callback")
SCOPES = os.getenv("SPOTIFY_SCOPES", "playlist-read-private playlist-read-collaborative").split()

def oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        cache_path=".spotipy_cache"
    )

@app.get("/login")
def login():
    return redirect(oauth().get_authorize_url())

@app.get("/callback")
def callback():
    code = request.args.get("code")
    oauth_mgr = oauth()
    oauth_mgr.get_access_token(code, as_dict=False)
    return redirect(os.getenv("FRONTEND_ORIGIN","http://localhost:5173"))

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

    sp = spotipy.Spotify(auth_manager=oauth())
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
    return jsonify(tracks)

@app.post("/api/save_tier")
def save_tier():
    body = request.get_json() or {}
    user = (body.get("user") or "").strip().lower()
    pid  = (body.get("playlistId") or "").strip()
    data = body.get("data")
    if not user or not pid or data is None:
        return jsonify({"error": "missing_fields"}), 400
    s = SessionLocal()
    try:
        row = s.query(TierSave).filter_by(user=user, playlist_id=pid).first()
        payload = json.dumps(data, separators=(",",":"))
        if row:
            row.data_json = payload
        else:
            row = TierSave(user=user, playlist_id=pid, data_json=payload)
            s.add(row)
        s.commit()
        return jsonify({"status": "ok"})
    finally:
        s.close()

@app.get("/api/load_tier")
def load_tier():
    user = (request.args.get("user") or "").strip().lower()
    pid  = (request.args.get("playlistId") or "").strip()
    if not user or not pid:
        return jsonify({"error": "missing_fields"}), 400
    s = SessionLocal()
    try:
        row = s.query(TierSave).filter_by(user=user, playlist_id=pid).first()
        if not row:
            return jsonify({"found": False})
        return jsonify({"found": True, "data": json.loads(row.data_json)})
    finally:
        s.close()

@app.get("/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
