import { fmt } from "./format";
import { ComparisonCard } from "./ComparisonCard";

export function ComparisonResults({
  selected,
  mode,
  result,
  loading,
  error,
  onRetry,
}) {
  return (
    <section className="results" aria-live="polite" aria-busy={loading}>
      <div className="results-heading">
        <span className="section-label">02 / EXPLORE THE COMPARISONS</span>
        <span className="distance-key">PER 36 MINUTES</span>
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
          <p>Comparing season-relative six-stat profiles.</p>
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
            <p className="reference-stats-label" id="reference-stats-label">
              Per-36 statistics
            </p>
            <dl className="reference-stats" aria-labelledby="reference-stats-label">
              {["PTS", "AST", "REB", "STL", "BLK", "TOV"].map((stat) => (
                <div key={stat}>
                  <dt>{stat}</dt>
                  <dd>{fmt(result.reference[mode][stat], 2)}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="summary">
            <span>
              {result.comparisons.length} closest comparisons{" "}
              <small>from {result.candidate_count} eligible historical player-seasons</small>
            </span>
            <span className="distance-key">LOWER DISTANCE = CLOSER</span>
          </div>
          {!result.comparisons.length && (
            <div className="error">
              <h3>No eligible comparisons</h3>
              <p>
                No eligible historical player-seasons have complete, reliable six-stat per-36 profiles.
              </p>
            </div>
          )}
          <div className="cards">
            {result.comparisons.map((comparison, index) => (
              <ComparisonCard
                key={`${comparison.player_id}-${comparison.season}`}
                c={comparison}
                i={index}
                mode={mode}
                referenceName={result.reference.name}
              />
            ))}
          </div>
          <div className="warnings">
            <h3>Read the numbers with context.</h3>
            <p>{result.coverage?.excluded_player_seasons} player-seasons excluded for incomplete statistics, unreliable minutes or unresolved duplicate games.</p>
            {result.warnings.map((w, i) => (
              <p key={i}>{w}</p>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
