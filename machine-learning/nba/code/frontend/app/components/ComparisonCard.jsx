import { fmt } from "./format";

const stats = ["PTS", "AST", "REB", "STL", "BLK", "TOV"];

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

export function ComparisonCard({ c, i, mode, referenceName }) {
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

