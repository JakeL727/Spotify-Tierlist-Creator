# backend/app.py
import os, re, json
from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# Configure session for production
app.config['SESSION_COOKIE_SECURE'] = True  # Use secure cookies in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cross-site requests

CORS(app, origins=os.getenv("FRONTEND_ORIGIN","*"), supports_credentials=True)

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:5000/callback")
SCOPES = os.getenv("SPOTIFY_SCOPES", "playlist-read-private playlist-read-collaborative").split()

# Client credentials for public playlist access
client_credentials_manager = SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)

def oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        cache_path=None  # Remove shared cache for security
    )

def get_user_spotify():
    """Get Spotify instance for the current user from session"""
    token_info = session.get('token_info')
    if not token_info:
        return None
    
    # Check if token is expired
    if oauth().is_token_expired(token_info):
        return None
    
    return spotipy.Spotify(auth=token_info['access_token'])

@app.get("/login")
def login():
    return redirect(oauth().get_authorize_url())

@app.get("/callback")
def callback():
    code = request.args.get("code")
    oauth_mgr = oauth()
    token_info = oauth_mgr.get_access_token(code, as_dict=True)
    
    # Store token in session for this user
    session['token_info'] = token_info
    print(f"Callback: Stored token in session for user")  # Debug log
    
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

    # Try to get playlist info first to determine if it's public or private
    try:
        # First try with client credentials (public playlists only)
        sp_public = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        playlist_info = sp_public.playlist(pid)
        
        # If we can access it with client credentials, it's public
        sp = sp_public
        is_public = True
        
    except Exception as e:
        # If client credentials fail, try with user authentication
        try:
            sp = get_user_spotify()
            if not sp:
                return jsonify({"error": "playlist_not_accessible", "message": "This playlist is private or doesn't exist. Please log in to access private playlists."}), 403
            
            playlist_info = sp.playlist(pid)
            is_public = False
        except Exception as auth_error:
            return jsonify({"error": "playlist_not_accessible", "message": "This playlist is private or doesn't exist. Please log in to access private playlists."}), 403

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
        "playlist_name": playlist_info.get("name", "Unknown Playlist"),
        "is_public": is_public
    })

@app.get("/api/auth_status")
def auth_status():
    """Check if user is authenticated"""
    try:
        print(f"Session data: {dict(session)}")  # Debug log
        sp = get_user_spotify()
        if not sp:
            print("No Spotify instance - not authenticated")  # Debug log
            return jsonify({"authenticated": False})
        
        user_info = sp.current_user()
        print(f"User authenticated: {user_info.get('display_name')}")  # Debug log
        return jsonify({
            "authenticated": True,
            "user": {
                "id": user_info.get("id"),
                "display_name": user_info.get("display_name"),
                "email": user_info.get("email")
            }
        })
    except Exception as e:
        print(f"Auth status error: {e}")  # Debug log
        return jsonify({"authenticated": False})

@app.get("/api/logout")
def logout():
    """Logout user by clearing session"""
    # Clear session data for this user
    session.pop('token_info', None)
    return jsonify({"status": "logged_out"})

@app.get("/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
