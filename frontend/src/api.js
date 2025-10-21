const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

export async function fetchPlaylistTracks(q) {
  const r = await fetch(`${API}/api/playlist?` + new URLSearchParams({ q }));
  if (!r.ok) throw new Error("Failed to fetch playlist");
  return r.json();
}