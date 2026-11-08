// Presentational UI; fetching, selection and request lifecycle remain in page.jsx.
const stats = ["PTS", "AST", "REB", "STL", "BLK", "TOV"];
const fmt = (n, digits = 1) =>
  typeof n === "number"
    ? n.toLocaleString("en-US", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      })
    : "—";

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

function StatisticalExplanation({ comparison }) {
  return (
    <details>
      <summary>
        Why this comparison? <span>+</span>
      </summary>
      <p>
        Each statistic has equal weight after standardization. The contributions
        below sum to squared distance. They explain the calculation, not player
        quality.
      </p>
      <div className="contributions">
        {stats.map((s) => (
          <div key={s}>
            <span>{s}</span>
            <meter
              aria-label={`${s} share of squared distance`}
              value={comparison.features[s].squared_distance_contribution}
              min="0"
              max={Math.max(comparison.distance ** 2, 0.001)}
            />
            <strong>
              {fmt(comparison.features[s].squared_distance_contribution, 3)}
            </strong>
          </div>
        ))}
      </div>
    </details>
  );
}

function ComparisonCard({ c, i, mode, referenceName }) {
  return (
    <article className="comparison" key={c.player_id}>
      <div className="card-top">
        <span className="rank">{String(i + 1).padStart(2, "0")}</span>
        <div className="card-name">
          <h3>{c.name}</h3>
          <p>
            {c.checkpoint.games} games ·{" "}
            {fmt(c.checkpoint.cumulative_minutes, 0)} min ·{" "}
            {c.checkpoint.GAME_DATE}
          </p>
          <p>
            {c.minute_difference_percent >= 0 ? "+" : ""}
            {fmt(c.minute_difference_percent)}% minutes vs reference
          </p>
        </div>
        <div className="score">
          <strong>{fmt(c.distance, 3)}</strong>
          <span>DISTANCE</span>
        </div>
      </div>
      <div className="table-scroll">
        <table>
          <caption>
            {mode === "per36" ? "Per-36" : "Per-game"} statistics ·{" "}
            {referenceName} vs {c.name}
          </caption>
          <thead>
            <tr>
              <th>STAT</th>
              <th>REFERENCE</th>
              <th>MATCH</th>
              <th>DIFFERENCE</th>
            </tr>
          </thead>
          <tbody>
            {stats.map((s) => (
              <tr key={s}>
                <th>{s}</th>
                <td>{fmt(c.features[s].reference, 2)}</td>
                <td>{fmt(c.features[s].comparison, 2)}</td>
                <td className="delta">
                  {c.features[s].difference > 0 ? "+" : ""}
                  {fmt(c.features[s].difference, 2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <StatisticalExplanation comparison={c} />
    </article>
  );
}

export function ComparisonResults({
  selected,
  mode,
  onModeChange,
  result,
  loading,
  error,
  onRetry,
}) {
  return (
    <section className="results" aria-live="polite" aria-busy={loading}>
      <div className="results-heading">
        <span className="section-label">02 / EXPLORE THE COMPARISONS</span>
        <div className="modes" role="group" aria-label="Statistics mode">
          <button
            aria-pressed={mode === "per36"}
            onClick={() => onModeChange("per36")}
          >
            Per 36 min
          </button>
          <button
            aria-pressed={mode === "per_game"}
            onClick={() => onModeChange("per_game")}
          >
            Per game
          </button>
        </div>
      </div>
      {!selected && (
        <div className="empty">
          <div className="court" aria-hidden="true">
            <div />
          </div>
          <h2>Every player has a neighborhood.</h2>
          <p>
            Select a player to explore their five closest statistical
            comparisons.
          </p>
          <span>PTS / AST / REB / STL / BLK / TOV</span>
        </div>
      )}
      {loading && (
        <div className="empty">
          <div className="spinner" />
          <h2>Finding statistical neighbors…</h2>
          <p>Matching season minutes and comparing six features.</p>
        </div>
      )}
      {error && (
        <div className="error" role="alert">
          <h2>We couldn’t load these comparisons.</h2>
          <p>{error}</p>
          <button className="retry" onClick={() => onRetry()}>
            Retry comparisons
          </button>
        </div>
      )}
      {result && (
        <>
          <div className="reference">
            <p className="eyebrow">REFERENCE PLAYER</p>
            <h2>{result.reference.name}</h2>
            <div className="exposure">
              <span>
                <strong>{result.reference.games}</strong> games
              </span>
              <span>
                <strong>{fmt(result.reference.cumulative_minutes, 0)}</strong>{" "}
                season minutes
              </span>
              <span>Through {result.reference.GAME_DATE}</span>
            </div>
          </div>
          <div className="summary">
            <span>
              {result.comparisons.length} closest comparisons{" "}
              <small>from {result.candidate_count} eligible players</small>
            </span>
            <span className="distance-key">LOWER DISTANCE = CLOSER</span>
          </div>
          {!result.comparisons.length && (
            <div className="error">
              <h3>No eligible comparisons</h3>
              <p>
                No other players qualify within the fixed ±10% minute window.
                The window has not been widened.
              </p>
            </div>
          )}
          <div className="cards">
            {result.comparisons.map((comparison, index) => (
              <ComparisonCard
                key={comparison.player_id}
                c={comparison}
                i={index}
                mode={mode}
                referenceName={result.reference.name}
              />
            ))}
          </div>
          <div className="warnings">
            <h3>Read the numbers with context.</h3>
            {result.warnings.map((w, i) => (
              <p key={i}>{w}</p>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
