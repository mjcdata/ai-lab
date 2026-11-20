"use client";
import { useEffect, useRef, useState } from "react";
import { SiteHeader } from "./components/SiteHeader";
import { Headline } from "./components/Headline";
import { SiteFooter } from "./components/SiteFooter";
import { PlayerSearch } from "./components/PlayerSearch";
import { ComparisonResults } from "./components/ComparisonResults";
import { searchPlayers, loadComparisons } from "../lib/data";

export default function Home() {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState([]);
  const [searchStatus, setSearchStatus] = useState("ready");
  const [searchError, setSearchError] = useState("");
  const [selected, setSelected] = useState(null);
  const mode = "per36";
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const resultHeadingRef = useRef(null);
  const focusOnResultRef = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    setSearchStatus("loading");
    setSearchError("");
    setPlayers([]);
    if (!query.trim()) {
      setSearchStatus("ready");
      return () => controller.abort();
    }
    searchPlayers(query, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setPlayers(data.players);
          setSearchStatus("ready");
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted && err.name !== "AbortError") {
          setSearchError(err.message);
          setSearchStatus("error");
        }
      });
    return () => controller.abort();
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
  useEffect(() => {
    const heading = resultHeadingRef.current;
    if (!result || !heading || !focusOnResultRef.current) return;
    focusOnResultRef.current = false;
    heading.focus({ preventScroll: true });
    if (window.matchMedia("(max-width: 650px)").matches) {
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      heading.scrollIntoView({ behavior: reducedMotion ? "instant" : "smooth", block: "start" });
    }
  }, [result]);
  return (
    <main>
      <SiteHeader />
      <Headline />
      <div className="workspace">
        <PlayerSearch
          query={query}
          onQueryChange={(value) => {
            focusOnResultRef.current = false;
            setQuery(value);
          }}
          players={players}
          searchStatus={searchStatus}
          searchError={searchError}
          selected={selected}
          onSelect={(player) => {
            focusOnResultRef.current = true;
            setSelected({ ...player });
          }}
          onRetry={() => setRetry((n) => n + 1)}
        />
        <ComparisonResults
          selected={selected}
          resultHeadingRef={resultHeadingRef}
          mode={mode}
          result={result}
          loading={loading}
          error={error}
          onRetry={() => {
            focusOnResultRef.current = true;
            setRetry((n) => n + 1);
          }}
        />
      </div>
      <SiteFooter />
    </main>
  );
}
