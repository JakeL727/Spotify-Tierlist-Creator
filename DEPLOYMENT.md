# Deployment Guide: Vercel + Railway

This guide will help you deploy your Spotify Tierlist app to production using Vercel (frontend) and Railway (backend).

## Prerequisites

1. **GitHub Account** - Your code needs to be in a GitHub repository
2. **Spotify Developer Account** - Get API credentials from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
3. **Vercel Account** - Sign up at [vercel.com](https://vercel.com)
4. **Railway Account** - Sign up at [railway.app](https://railway.app)

## Step 1: Get Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Note down your **Client ID** and **Client Secret**
4. No redirect URIs needed for public playlist access

## Step 2: Deploy Backend to Railway

1. **Go to [railway.app](https://railway.app)** and sign up with GitHub

2. **Create a new project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your spotify-tierlist repository

3. **Configure the backend service:**
   - Railway should auto-detect it's a Python app
   - Set the root directory to `backend`
   - Railway will automatically install dependencies from `requirements.txt`

4. **Generate public domain:**
   - Click "Generate Domain" to get your public URL
   - Note your Railway app URL (something like `https://your-app.railway.app`)

5. **Set environment variables:**
   - Go to your backend service settings → Variables
   - Add these variables:
     ```
     SPOTIFY_CLIENT_ID=your_spotify_client_id
     SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
     FRONTEND_ORIGIN=https://your-vercel-app.vercel.app
     ```

6. **Deploy:**
   - Railway will automatically deploy when you push to GitHub
   - Your app should start successfully without any database setup

## Step 3: Deploy Frontend to Vercel

1. **Go to [vercel.com](https://vercel.com)** and sign up with GitHub

2. **Import your project:**
   - Click "New Project"
   - Import your GitHub repository
   - Set the root directory to `frontend`

3. **Configure build settings:**
   - Framework Preset: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`

4. **Set environment variables:**
   - Go to project settings → Environment Variables
   - Add:
     ```
     VITE_API_URL=https://your-railway-app.railway.app
     ```

5. **Deploy:**
   - Vercel will automatically deploy
   - Note your Vercel app URL (something like `https://your-app.vercel.app`)

## Step 4: Update Spotify App Settings

1. **No additional Spotify configuration needed** - public playlists work with just Client ID and Secret

## Step 5: Update Railway Environment Variables

Go back to Railway and update:
```
FRONTEND_ORIGIN=https://your-vercel-app.vercel.app
```

## Step 6: Test Your Deployment

1. Visit your Vercel frontend URL
2. **Test public playlists**: Paste any public Spotify playlist URL - should work immediately
3. **Test tier list creation**: Drag songs into tiers and export as PNG

## How the App Works

### Public Playlists Only
- Users can paste any public Spotify playlist URL
- App automatically loads tracks using Spotify's client credentials
- Works immediately without any authentication
- Private playlists are not supported

### Tier List Features
- Drag and drop songs into custom tiers
- Export tier lists as PNG images
- No account system - users download their tier lists locally

## Troubleshooting

### Backend Issues
- Check Railway logs: Go to your service → Deployments → View logs
- Verify all environment variables are set correctly
- **No database errors**: The app no longer uses a database

### Frontend Issues
- Check Vercel function logs in the dashboard
- Verify `VITE_API_URL` environment variable is set
- Check browser console for CORS errors

### Common Issues
- **CORS errors**: Make sure `FRONTEND_ORIGIN` in Railway matches your Vercel URL exactly
- **Playlist not found**: Make sure you're using a public playlist URL
- **Public playlist not loading**: Check that `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are set correctly

## Cost

- **Vercel**: Free tier (generous limits for personal use)
- **Railway**: Free tier (500 hours/month)
- **Database**: $0 (no database needed!)
- **Total**: $0/month for personal use

## Automatic Deployments

Both platforms will automatically redeploy when you push changes to your GitHub repository:
- Push to `main` branch → automatic deployment
- No manual intervention needed after initial setup

## Local Development

To continue developing locally:
1. Copy `backend/env.example` to `backend/.env` and fill in your values
2. Copy `frontend/env.example` to `frontend/.env` and fill in your values
3. Run backend: `cd backend && python app.py`
4. Run frontend: `cd frontend && npm start`
