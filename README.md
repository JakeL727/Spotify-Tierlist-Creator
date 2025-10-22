# Spotify Tier List Creator

A web application that lets you create tier lists from public Spotify playlists. Users can drag and drop songs into custom tiers and export their tier lists as PNG images.

## Features

- **Public Playlist Access**: Load any public Spotify playlist
- **Drag & Drop Interface**: Intuitive tier list creation with custom tiers
- **Export Functionality**: Download tier lists as high-quality PNG images
- **No Account Required**: No user accounts or data storage - everything is local

## How It Works

1. Paste any public Spotify playlist URL
2. App automatically loads tracks using Spotify's client credentials
3. Drag songs from the "Unranked Songs" section into your custom tiers
4. Customize tier names, colors, and order in settings
5. Export your completed tier list as a PNG image

## Tech Stack

- **Frontend**: React + Vite + DnD Kit
- **Backend**: Flask + Spotipy
- **Deployment**: Vercel (frontend) + Railway (backend)

## Local Development

### Backend Setup
```bash
cd backend
cp env.example .env
# Edit .env with your Spotify API credentials
pip install -r requirements.txt
python app.py
```

### Frontend Setup
```bash
cd frontend
cp env.example .env
# Edit .env with your backend URL
npm install
npm run dev
```

## Environment Variables

### Backend (.env)
```
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
FRONTEND_ORIGIN=http://localhost:5173
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:5000
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions using Vercel and Railway.

## Spotify API Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Copy your Client ID and Client Secret
4. No redirect URIs needed for public playlist access

## License

MIT License - feel free to use this project for your own tier list creations!
