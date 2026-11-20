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
      <label htmlFor="search">Find your player</label>
      <div className="search-box">
        <span aria-hidden="true">⌕</span>
        <input
          id="search"
          type="search"
          aria-controls="player-search-results"
          placeholder="Try Curry, Jokić, Bronny…"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          autoComplete="off"
        />
      </div>
      <div
        id="player-search-results"
        className="roster"
        aria-live="polite"
        aria-busy={searchStatus === "loading"}
      >
        {query.trim() && searchStatus === "loading" && (
          <p className="status">Searching roster…</p>
        )}
        {query.trim() && searchError && (
          <div role="alert">
            <p>{searchError}</p>
            <button className="retry" onClick={() => onRetry()}>
              Retry search
            </button>
          </div>
        )}
        {query.trim() && searchStatus === "ready" && !players.length && (
          <p className="status">No players found. Try a different name.</p>
        )}
        {query.trim() && players.map((p) => (
          <button
            type="button"
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
          </button>
        ))}
      </div>
    </aside>
  );
}

