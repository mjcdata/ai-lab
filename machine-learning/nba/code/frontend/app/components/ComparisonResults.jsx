import { fmt } from "./format";
import { ComparisonCard } from "./ComparisonCard";

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
