import { fmt } from "./format";

export function PlayerSearch({
  query,
  onQueryChange,
  players,
  searchStatus,
  searchError,
  selected,
  onSelect,
  onRetry,
}) {
  return (
    <aside className="picker">
      <div className="section-label">
        <span>01 / SELECT A PLAYER</span>
        <span>↗</span>
      </div>
      <label htmlFor="search">Search the 2024–25 roster</label>
      <div className="search-box">
        <span aria-hidden="true">⌕</span>
        <input
          id="search"
          placeholder="Try Curry, Jokić, Bronny…"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          autoComplete="off"
        />
      </div>
      <p className="hint">
        Search by name or player ID. Showing up to 25 matches; refine your
        search.
      </p>
      <div
        className="roster"
        aria-live="polite"
        aria-busy={searchStatus === "loading"}
      >
        {searchStatus === "loading" && (
          <p className="status">Searching roster…</p>
        )}
        {searchError && (
          <div role="alert">
            <p>{searchError}</p>
            <button className="retry" onClick={() => onRetry()}>
              Retry search
            </button>
          </div>
        )}
        {searchStatus === "ready" && !players.length && (
          <p className="status">No players found. Try a different name.</p>
        )}
        {players.map((p) => (
          <button
            className={`player-option ${selected?.player_id === p.player_id ? "active" : ""}`}
            key={p.player_id}
            onClick={() => onSelect(p)}
            aria-pressed={selected?.player_id === p.player_id}
          >
            <span>
              <strong>{p.name}</strong>
              <small>
                {p.games} games · {fmt(p.minutes, 0)} min
              </small>
            </span>
            <span aria-hidden="true">↗</span>
          </button>
        ))}
      </div>
    </aside>
  );
}

