import { fmt } from "./format";

const stats = ["PTS", "AST", "REB", "STL", "BLK", "TOV"];

function StatisticalExplanation({ comparison }) {
  return (
    <details>
      <summary>
        Why this comparison? <span>+</span>
      </summary>
      <p>
        Each statistic has equal weight after standardization against its own season. The contributions
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
          <h3>{c.name} · {c.season}</h3>
          <p>
            {c.checkpoint.games} games ·{" "}
            {fmt(c.checkpoint.cumulative_minutes, 0)} min ·{" "}
            {c.checkpoint.GAME_DATE}
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
            Per-36 statistics ·{" "}
            {referenceName} vs {c.name}
          </caption>
          <thead>
            <tr>
              <th>STAT</th>
              <th>REFERENCE</th>
              <th>MATCH</th>
              <th>DIFFERENCE</th>
              <th>REF Z</th><th>MATCH Z</th>
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
                <td>{fmt(c.features[s].reference_z, 2)}</td>
                <td>{fmt(c.features[s].comparison_z, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <StatisticalExplanation comparison={c} />
    </article>
  );
}

