import React, { useMemo, useRef, useState } from "react";
import {
  DndContext,
  pointerWithin,
  useDroppable,
  DragOverlay,
  useSensor,
  useSensors,
  PointerSensor,
  MouseSensor,
  TouchSensor,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  rectSortingStrategy,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import * as htmlToImage from "html-to-image";
import { fetchPlaylistTracks, checkAuthStatus, logout } from "./api";
import { Analytics } from "@vercel/analytics/react";

/* ---------- helpers ---------- */
function defaultColorForTier(t) {
  switch (t) {
    case "S": return "#ff595e";
    case "A": return "#ffca3a";
    case "B": return "#8ac926";
    case "C": return "#1982c4";
    case "D": return "#6a4c93";
    case "F": return "#9aa4ad";
    default: return "#8aa4ff";
  }
}
function nextTierId(existing) {
  let i = 1;
  while (existing.includes(`T${i}`)) i++;
  return `T${i}`;
}

/* ---------- UI bits ---------- */
function Tile({ item, dragging, compact }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: item.id });
  const style = dragging ? {} : { transform: CSS.Transform.toString(transform), transition };

  return (
    <div
      className={`tile${isDragging ? " is-dragging" : ""}${compact ? " compact" : ""}`}
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
    >
      <img className="tile-img" src={item.albumArt} alt="" />
      <div className={`tile-meta${compact ? " compact" : ""}`}>
        <div className={`tile-title${compact ? " compact" : ""}`} title={item.name}>
          {item.name}
        </div>
        {!compact && <div className="tile-artist" title={item.artists}>{item.artists}</div>}
      </div>
    </div>
  );
}

function Droppable({ id, className, children }) {
  const { setNodeRef } = useDroppable({ id });
  return (
    <div ref={setNodeRef} id={id} className={className}>
      {children}
    </div>
  );
}

function TierRow({ id, items, label, color, children }) {
  const { setNodeRef } = useDroppable({ id });
  return (
    <div className="tier-row" ref={setNodeRef} id={id}>
      <div className="tier-badge" style={{ background: color }}>
        <span className="tier-badge-text">{label || " "}</span>
      </div>
      <div className="tier-drop">
        <SortableContext items={items.map(x => x.id)} strategy={rectSortingStrategy}>
          {children}
        </SortableContext>
      </div>
    </div>
  );
}

function CogIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="currentColor" d="M12 8a4 4 0 100 8 4 4 0 000-8zm9.4 4a7.4 7.4 0 01-.1 1l2.1 1.6-2 3.5-2.5-1a7.7 7.7 0 01-1.8 1l-.4 2.7H9.3l-.4-2.7a7.7 7.7 0 01-1.9-1l-2.5 1-2-3.5 2.1-1.6a7.4 7.4 0 010-2L.5 9.4l2-3.5 2.5 1a7.7 7.7 0 011.9-1l.4-2.7h4.3l.4 2.7a7.7 7.7 0 011.8 1l2.5-1 2 3.5-2.1 1.6c.1.3.1.7.1 1z"/>
    </svg>
  );
}

/* ---------- App ---------- */
export default function App() {
  // Theme & layout (dark by default)
  const [dark, setDark] = useState(true);
  const [compact, setCompact] = useState(false);

  // Core tiers (live)
  const [tiers, setTiers] = useState(["S","A","B","C","D","F"]);
  const [tierLabels, setTierLabels] = useState(
    Object.fromEntries(["S","A","B","C","D","F"].map(t => [t, t]))
  );
  const [tierColors, setTierColors] = useState(
    Object.fromEntries(["S","A","B","C","D","F"].map(t => [t, defaultColorForTier(t)]))
  );

  // Data
  const [playlistUrl, setPlaylistUrl] = useState("");
  const [pool, setPool] = useState([]);
  const [lanes, setLanes] = useState(Object.fromEntries(["S","A","B","C","D","F"].map(t => [t, []])));
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [activeId, setActiveId] = useState(null);
  
  // Authentication
  const [authStatus, setAuthStatus] = useState({ authenticated: false });
  const [playlistName, setPlaylistName] = useState("");

  // SETTINGS state
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [draftTiers, setDraftTiers] = useState(tiers);
  const [draftLabels, setDraftLabels] = useState(tierLabels);
  const [draftColors, setDraftColors] = useState(tierColors);
  const [settingsTypingId, setSettingsTypingId] = useState(null);

  // Sensors
  const boardSensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const settingsSensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 6 } })
  );

  const tiersRef = useRef(null);

  // Check authentication status on app load
  React.useEffect(() => {
    checkAuthStatus().then(setAuthStatus);
  }, []);

  const filteredPool = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return pool;
    return pool.filter(
      it =>
        (it.name || "").toLowerCase().includes(q) ||
        (it.artists || "").toLowerCase().includes(q)
    );
  }, [pool, filter]);

  async function loadPlaylist() {
    try {
      setErr(""); setLoading(true);
      const response = await fetch(`${import.meta.env.VITE_API_URL || "http://localhost:5000"}/api/playlist?` + new URLSearchParams({ q: playlistUrl }));
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to fetch playlist");
      }
      
      const data = await response.json();
      const tracks = data.tracks;
      const seen = new Set();
      const dedup = tracks.filter(t => t.id && !seen.has(t.id) && seen.add(t.id));
      setPool(dedup);
      setLanes(Object.fromEntries(tiers.map(t => [t, []])));
      setPlaylistName(data.playlist_name || "Unknown Playlist");
      
      // Update auth status if we got user info
      if (data.is_public === false) {
        checkAuthStatus().then(setAuthStatus);
      }
    } catch (e) {
      setErr(e.message || "Failed to load playlist");
    } finally {
      setLoading(false);
    }
  }

  /* ----- drag helpers & handlers ----- */
  function containerOf(id) {
    if (id === "POOL") return "POOL";
    if (pool.some(x => x.id === id)) return "POOL";
    for (const t of tiers) if ((lanes[t] || []).some(x => x.id === id)) return t;
    return null;
  }
  function itemById(id) {
    return pool.find(x => x.id === id) || tiers.flatMap(t => lanes[t] || []).find(x => x.id === id);
  }

  function onDragStart(e) { setActiveId(e.active.id); }

  function onDragEnd(e) {
    const { active, over } = e;
    setActiveId(null);
    if (!over) return; // dropped outside → snap back (no state change)

    const from = containerOf(active.id);
    const possibleTargets = ["POOL", ...tiers];
    const to   = possibleTargets.includes(over.id) ? over.id : containerOf(over.id);
    const overId = possibleTargets.includes(over.id) ? null : over.id;

    if (!from || !to) return;

    // same container reorder (forward & backward)
    if (from === to) {
      if (from === "POOL") {
        const oldIndex = pool.findIndex(x => x.id === active.id);
        const newIndex = overId ? pool.findIndex(x => x.id === overId) : pool.length - 1;
        if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
          setPool(prev => arrayMove(prev, oldIndex, newIndex));
        }
      } else {
        const arr = lanes[from] || [];
        const oldIndex = arr.findIndex(x => x.id === active.id);
        const newIndex = overId ? arr.findIndex(x => x.id === overId) : arr.length - 1;
        if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
          const moved = arrayMove(arr, oldIndex, newIndex);
          setLanes(prev => ({ ...prev, [from]: moved }));
        }
      }
      return;
    }

    // across containers
    const removeFrom = (arr, id) => {
      const idx = arr.findIndex(x => x.id === id);
      if (idx === -1) return { arr, item: null };
      const copy = arr.slice(); const [itm] = copy.splice(idx, 1);
      return { arr: copy, item: itm };
    };
    const insertBefore = (arr, item, beforeId) => {
      if (!beforeId) return [...arr, item];
      const idx = arr.findIndex(x => x.id === beforeId);
      return idx === -1 ? [...arr, item] : [...arr.slice(0, idx), item, ...arr.slice(idx)];
    };

    if (from === "POOL") {
      const { arr: poolLess, item } = removeFrom(pool, active.id);
      if (!item) return;
      setPool(poolLess);
      setLanes(prev => ({ ...prev, [to]: insertBefore(prev[to] || [], item, overId) }));
    } else {
      const { arr: srcLess, item } = removeFrom(lanes[from] || [], active.id);
      if (!item) return;
      if (to === "POOL") {
        setLanes(prev => ({ ...prev, [from]: srcLess }));
        setPool(prev => insertBefore(prev, item, overId));
      } else {
        setLanes(prev => ({
          ...prev,
          [from]: srcLess,
          [to]: insertBefore(prev[to] || [], item, overId),
        }));
      }
    }
  }

  function onDragCancel() { setActiveId(null); }

  /* ----- actions ----- */
  async function exportPNG() {
    if (!tiersRef.current) return;
    const url = await htmlToImage.toPng(tiersRef.current, { pixelRatio: 2 });
    const a = document.createElement("a"); a.href = url; a.download = `${playlistName || 'tier-list'}.png`; a.click();
  }

  async function handleLogout() {
    await logout();
    setAuthStatus({ authenticated: false });
  }

  function openSettings() {
    setDraftTiers(tiers);
    setDraftLabels(tierLabels);
    setDraftColors(tierColors);
    setSettingsOpen(true);
  }
  function cancelSettings() { setSettingsOpen(false); }
  function saveSettings() {
    const removed = tiers.filter(t => !draftTiers.includes(t));
    const removedItems = removed.flatMap(t => lanes[t] || []);
    const newLanes = Object.fromEntries(draftTiers.map(t => [t, lanes[t] ? [...lanes[t]] : []]));
    setPool(prev => [...removedItems, ...prev]);
    setTiers(draftTiers);
    setTierLabels(draftLabels);
    setTierColors(draftColors);
    setLanes(newLanes);
    setSettingsOpen(false);
  }

  function draftAddTier() {
    const id = nextTierId(draftTiers);
    setDraftTiers(prev => [...prev, id]);
    setDraftLabels(prev => ({ ...prev, [id]: "" }));
    setDraftColors(prev => ({ ...prev, [id]: defaultColorForTier(id) }));
  }
  function draftDeleteTier(id) {
    setDraftTiers(prev => prev.filter(t => t !== id));
    setDraftLabels(prev => { const p = { ...prev }; delete p[id]; return p; });
    setDraftColors(prev => { const p = { ...prev }; delete p[id]; return p; });
  }
  function draftUpdateLabel(id, value) { setDraftLabels(prev => ({ ...prev, [id]: value })); }
  function draftUpdateColor(id, value) { setDraftColors(prev => ({ ...prev, [id]: value })); }

  /* ----- SettingsRow (inside App so it sees draft state) ----- */
  const SettingsRow = ({ id }) => {
  const {
    setNodeRef,
    setActivatorNodeRef,
    attributes,
    listeners,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled: settingsTypingId === id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  };

  const [localValue, setLocalValue] = useState(draftLabels[id] ?? "");
  React.useEffect(() => { setLocalValue(draftLabels[id] ?? ""); }, [id, draftLabels]);

  function handleBlur() {
    draftUpdateLabel(id, localValue);
    setSettingsTypingId(null);
  }

  // Stop DnD from intercepting the press that should focus the inputs
  const stopPress = (e) => { e.stopPropagation(); };

  return (
    <div className="settings-row" ref={setNodeRef} style={style}>
      <button
        className="drag-handle icon-btn"
        title="Drag to reorder"
        ref={setActivatorNodeRef}
        {...attributes}
        {...listeners}
      >
        ☰
      </button>

      <input
        className="input small"
        value={localValue}
        onChange={(e)=>setLocalValue(e.target.value)}
        placeholder="Insert name here…"
        onPointerDown={stopPress}
        onMouseDown={stopPress}
        onFocus={(e)=>{ setSettingsTypingId(id); e.target.select(); }}
        onBlur={handleBlur}
        style={{ touchAction: "manipulation" }}
      />

      <input
        type="color"
        className="color-input"
        value={draftColors[id] || defaultColorForTier(id)}
        onChange={(e)=>draftUpdateColor(id, e.target.value)}
        title="Pick color"
        onPointerDown={stopPress}
        onMouseDown={stopPress}
        style={{ touchAction: "manipulation" }}
      />

      <button className="btn danger" onClick={() => draftDeleteTier(id)}>Delete</button>
    </div>
  );
};

  function onSettingsDragEnd(e) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const oldIndex = draftTiers.indexOf(active.id);
    const newIndex = draftTiers.indexOf(over.id);
    if (oldIndex === -1 || newIndex === -1) return;
    setDraftTiers(prev => arrayMove(prev, oldIndex, newIndex));
  }

  const activeItem = activeId ? itemById(activeId) : null;

  return (
    <div className={`wrap ${dark ? "theme-dark" : "theme-light"}`}>
      <div className="topbar">
        <h1>Spotify Tier List</h1>
        <div className="topbar-actions">
          <button className="icon-btn" title="Settings" onClick={openSettings}><CogIcon /></button>
          <button className="btn ghost" onClick={() => setDark(d => !d)}>
            {dark ? "☀️ Light Mode" : "🌙 Dark Mode"}
          </button>
        </div>
      </div>

      <div className="row">
        <input className="input" placeholder="Paste Spotify playlist link"
          value={playlistUrl} onChange={(e)=>setPlaylistUrl(e.target.value)} />
        <button className="btn" onClick={loadPlaylist} disabled={loading}>
          {loading ? "Loading…" : "Load"}
        </button>
        {authStatus.authenticated ? (
          <button className="btn ghost" onClick={handleLogout}>
            Logout ({authStatus.user?.display_name || 'User'})
          </button>
        ) : (
          <a className="btn ghost" href={`${import.meta.env.VITE_API_URL || "http://localhost:5000"}/login`} target="_blank" rel="noreferrer">
            Login for Private Playlists
          </a>
        )}
        <button className="btn" onClick={exportPNG}>Export PNG</button>
      </div>

      <p className="disclaimer">
        🔒 <b>Public playlists</b> work without login. <b>Private playlists</b> require Spotify authentication.
        {authStatus.authenticated && " ✅ You're logged in and can access private playlists."}
      </p>

      <DndContext
        sensors={boardSensors}
        collisionDetection={pointerWithin}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
        onDragCancel={onDragCancel}
      >
        <div className="board">
          {/* TIERS */}
          <section className="tiers" ref={tiersRef}>
            {tiers.map(t => (
              <TierRow key={t} id={t} items={lanes[t] || []}
                label={tierLabels[t] ?? ""} color={tierColors[t] || defaultColorForTier(t)}>
                {(lanes[t] || []).map(item => <Tile key={item.id} item={item} compact={compact} />)}
              </TierRow>
            ))}
          </section>

          {/* SEARCH */}
          <div className="row search under-tiers">
            <input className="input" placeholder="Search unranked by title/artist…"
              value={filter} onChange={(e)=>setFilter(e.target.value)} />
          </div>

          {/* POOL */}
          <section className="pool">
            <div className="pool-header">
              <h2>Unranked Songs</h2>
              <div className="pool-actions">
                <div className="pool-count">{filteredPool.length} {filteredPool.length === 1 ? "song" : "songs"}</div>
                <button className="btn ghost" onClick={() => setCompact(c => !c)}>
                  {compact ? "Large View" : "Compact View"}
                </button>
              </div>
            </div>
            <Droppable id="POOL" className={`pool-grid${compact ? " compact" : ""}`}>
              <SortableContext items={filteredPool.map(x => x.id)} strategy={rectSortingStrategy}>
                {filteredPool.map(item => <Tile key={item.id} item={item} compact={compact} />)}
              </SortableContext>
            </Droppable>
          </section>
        </div>

        <DragOverlay adjustScale={false}>
          {activeItem ? <Tile item={activeItem} dragging compact={compact} /> : null}
        </DragOverlay>
      </DndContext>

      {/* SETTINGS */}
      {settingsOpen && (
        <div className="settings">
          <div className="settings-header">
            <h3>Settings</h3>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn" onClick={saveSettings}>Save</button>
              <button className="btn ghost" onClick={cancelSettings}>Cancel</button>
            </div>
          </div>
          <div className="settings-body">
            <div className="settings-group">
              <div className="settings-row">
                <button className="btn" onClick={draftAddTier}>+ Add Tier</button>
              </div>
              <DndContext sensors={settingsSensors} onDragEnd={onSettingsDragEnd}>
                <SortableContext items={draftTiers} strategy={verticalListSortingStrategy}>
                  {draftTiers.map(id => <SettingsRow key={id} id={id} />)}
                </SortableContext>
              </DndContext>
              <p className="hint">On <b>Save</b>, songs from deleted tiers move back to <b>Unranked</b>.</p>
            </div>
          </div>
        </div>
      )}

      {err && <div className="alert">{err}</div>}
      <Analytics />
    </div>
  );
}