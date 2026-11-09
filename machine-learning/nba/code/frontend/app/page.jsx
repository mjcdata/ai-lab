"use client";
import { useEffect, useState } from "react";
import { PlayerSearch } from "./components/PlayerSearch";
import { ComparisonResults } from "./components/ComparisonResults";
import { searchPlayers, loadComparisons } from "../lib/data";

export default function Home() {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState([]);
  const [searchStatus, setSearchStatus] = useState("loading");
  const [searchError, setSearchError] = useState("");
  const [selected, setSelected] = useState(null);
  const mode = "per36";
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setSearchStatus("loading");
    setSearchError("");
    setPlayers([]);
    const timer = setTimeout(() => {
      searchPlayers(query, controller.signal)
        .then((data) => {
          setPlayers(data.players);
          setSearchStatus("ready");
        })
        .catch((err) => {
          if (err.name !== "AbortError") {
            setSearchError(err.message);
            setSearchStatus("error");
          }
        });
    }, 220);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, retry]);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setResult(null);
    loadComparisons(selected.player_id, mode, controller.signal)
      .then(setResult)
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [selected, mode, retry]);
  return (
    <main>
      <header className="masthead">
        <a href="/" className="brand">
          <span className="mark">◉</span> NBA Player Similarity
        </a>
        <span className="edition">AI LAB / EXPERIMENT 001</span>
        <span className="season">2026–27 → HISTORICAL SEASONS</span>
      </header>
      <div className="workspace">
        <PlayerSearch
          query={query}
          onQueryChange={setQuery}
          players={players}
          searchStatus={searchStatus}
          searchError={searchError}
          selected={selected}
          onSelect={setSelected}
          onRetry={() => setRetry((n) => n + 1)}
        />
        <ComparisonResults
          selected={selected}
          mode={mode}
          result={result}
          loading={loading}
          error={error}
          onRetry={() => setRetry((n) => n + 1)}
        />
      </div>
      <footer>
        <strong>HOW IT WORKS</strong>
        <p>
          One record per player season →
          standardized six-stat profile → equal-weight Euclidean distance.
          Within-season population Z-scores. Per-36 only. No playing-time cutoff.
        </p>
        <span>
          Local research MVP · No shooting efficiency, position or age features
          · Distance is not a probability.
        </span>
        <p>Statistics source: <a href="https://www.nba.com/stats">NBA.com</a>. Independent research project.</p>
      </footer>
    </main>
  );
}
