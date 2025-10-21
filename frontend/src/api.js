const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

export async function fetchPlaylistTracks(q) {
  const r = await fetch(`${API}/api/playlist?` + new URLSearchParams({ q }));
  if (!r.ok) {
    const error = await r.json();
    throw new Error(error.message || "Failed to fetch playlist");
  }
  const data = await r.json();
  return data.tracks; // Extract tracks from the new response format
}

export async function checkAuthStatus() {
  try {
    const r = await fetch(`${API}/api/auth_status`);
    if (!r.ok) return { authenticated: false };
    return await r.json();
  } catch {
    return { authenticated: false };
  }
}

export async function logout() {
  try {
    await fetch(`${API}/api/logout`);
  } catch {
    // Ignore errors
  }
}