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
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cross-site requests (required for cross-domain)
app.config['SESSION_PERMANENT'] = False  # Session expires when browser closes

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
    # Use session-specific cache file for security
    session_id = session.get('session_id')
    if not session_id:
        # Generate a unique session ID if none exists
        import uuid
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    cache_path = f".spotipy_cache_{session_id}"
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        cache_path=cache_path
    )

def get_user_spotify():
    """Get Spotify instance for the current user from session or cache"""
    # Try session first
    token_info = session.get('token_info')
    
    if not token_info:
        # Fallback to cache file using session_id from session
        session_id = session.get('session_id')
        if session_id:
            try:
                cache_path = f".spotipy_cache_{session_id}"
                import os
                if os.path.exists(cache_path):
                    # Read and parse the cache file directly
                    with open(cache_path, 'r') as f:
                        import json
                        token_info = json.load(f)
                        # Check if token is expired
                        import time
                        if token_info.get('expires_at', 0) < time.time():
                            print(f"Token expired in cache file {cache_path}")
                            token_info = None
                        else:
                            print(f"Found valid token in cache file {cache_path}")
                else:
                    print(f"Cache file {cache_path} does not exist")
            except Exception as e:
                print(f"Cache check error in get_user_spotify: {e}")
                token_info = None
        else:
            print("No session_id found in session")
    
    if not token_info:
        print("No valid token found in get_user_spotify")
        return None
    
    # Check if session token is expired (for session-based tokens)
    if 'expires_at' in token_info:
        import time
        if token_info.get('expires_at', 0) < time.time():
            print("Session token is expired")
            return None
    
    print(f"Creating Spotify instance with token for user")
    return spotipy.Spotify(auth=token_info['access_token'])

@app.get("/login")
def login():
    # Generate session_id and store in session
    session_id = session.get('session_id')
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    # Create OAuth manager with this session_id
    oauth_mgr = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        cache_path=f".spotipy_cache_{session_id}",
        state=session_id  # Pass session_id as state parameter
    )
    
    return redirect(oauth_mgr.get_authorize_url())

@app.get("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")  # Extract session_id from state parameter
    
    # Use session_id from state parameter (passed from login)
    session_id = state
    if not session_id:
        print("Error: No state parameter received in callback")  # Debug log
        return redirect(os.getenv("FRONTEND_ORIGIN","http://localhost:5173"))
    
    # Store session_id in session for future requests
    session['session_id'] = session_id
    
    # Use the same cache path as login
    oauth_mgr = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        cache_path=f".spotipy_cache_{session_id}"
    )
    
    token_info = oauth_mgr.get_access_token(code, as_dict=True)
    
    # Store token in session for this user
    session['token_info'] = token_info
    print(f"Callback: Stored token in session for user {session_id}")  # Debug log
    
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
        error_msg = str(e)
        try:
            sp = get_user_spotify()
            if not sp:
                if "404" in error_msg or "not found" in error_msg.lower():
                    return jsonify({"error": "playlist_not_found", "message": "Playlist not found. Please check the playlist URL or ID."}), 404
                return jsonify({"error": "playlist_not_accessible", "message": "This playlist is private or doesn't exist. Please log in to access private playlists."}), 403
            
            playlist_info = sp.playlist(pid)
            is_public = False
        except Exception as auth_error:
            auth_error_msg = str(auth_error)
            if "404" in auth_error_msg or "not found" in auth_error_msg.lower():
                return jsonify({"error": "playlist_not_found", "message": "Playlist not found. Please check the playlist URL or ID."}), 404
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
    """Check if user is authenticated by testing Spotify API access"""
    try:
        print(f"Session data: {dict(session)}")  # Debug log
        
        # Try to get user Spotify instance
        sp = get_user_spotify()
        if not sp:
            print("No Spotify instance from session - trying alternative auth")  # Debug log
            
            # Try using the OAuth manager to get cached token
            try:
                oauth_mgr = oauth()
                token_info = oauth_mgr.get_cached_token()
                if token_info and not oauth_mgr.is_token_expired(token_info):
                    sp = spotipy.Spotify(auth=token_info['access_token'])
                    print("Found cached token, testing API access")  # Debug log
                else:
                    print("No valid cached token found")  # Debug log
                    return jsonify({"authenticated": False})
            except Exception as cache_error:
                print(f"Cache check error: {cache_error}")  # Debug log
                return jsonify({"authenticated": False})
        
        # Test actual API access
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
    """Logout user by clearing cached tokens"""
    try:
        # Get session ID before clearing session
        session_id = session.get('session_id')
        
        # Clear session data
        session.pop('token_info', None)
        session.pop('session_id', None)
        
        # Clear the user-specific cache file
        import os
        if session_id:
            cache_file = f".spotipy_cache_{session_id}"
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print(f"Logout: Removed user-specific cache file {cache_file}")  # Debug log
        
        print("Logout: Cleared session and user-specific cache file")  # Debug log
    except Exception as e:
        print(f"Logout error: {e}")  # Debug log
    
    return jsonify({"status": "logged_out"})

@app.get("/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
