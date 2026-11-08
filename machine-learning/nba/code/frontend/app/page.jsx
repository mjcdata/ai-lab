"use client";
import { useEffect, useState } from "react";
import { PlayerSearch } from "./components/PlayerSearch";
import { ComparisonResults } from "./components/ComparisonResults";
async function read(url, signal) {
  const response = await fetch(url, { signal });
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Unable to load results. Please retry.",
    );
  return data;
}
export default function Home() {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState([]);
  const [searchStatus, setSearchStatus] = useState("loading");
  const [searchError, setSearchError] = useState("");
  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState("per36");
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
      read(
        `/api/players?q=${encodeURIComponent(query)}&limit=25`,
        controller.signal,
      )
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
    read(
      `/api/players/${selected.player_id}/comparisons?mode=${mode}`,
      controller.signal,
    )
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
        <span className="season">2024–25 · REGULAR SEASON</span>
      </header>
      <section className="intro">
        <p className="eyebrow">THE PLAYER SIMILARITY LAB</p>
        <h1>
          NBA Player <br />
          <em>Similarity</em>
        </h1>
        <p className="lede">
          Find statistical neighbors at a similar point in their season. Six
          stats. Equal weight. A closer look at the game.
        </p>
        <div className="scope">
          <span className="dot" /> Season-to-date only · Not career comparisons
          or predictions
        </div>
      </section>
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
          onModeChange={setMode}
          result={result}
          loading={loading}
          error={error}
          onRetry={() => setRetry((n) => n + 1)}
        />
      </div>
      <footer>
        <strong>HOW IT WORKS</strong>
        <p>
          Nearest checkpoint within ±10% cumulative season minutes →
          standardized six-stat profile → equal-weight Euclidean distance.
          Original fixed scaler. No extra playing-time cutoff.
        </p>
        <span>
          Local research MVP · No shooting efficiency, position or age features
          · Distance is not a probability.
        </span>
      </footer>
    </main>
  );
}
