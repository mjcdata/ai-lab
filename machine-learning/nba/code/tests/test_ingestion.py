"""Offline pilot tests; no requests to stats.nba.com."""
import json
import tempfile
import unittest
from pathlib import Path
from nba_player_similarity.ingestion import (
    exclude_unresolved_duplicates, ingest, validate_rows, validate_season, run_batch, season_range,
)


def row(player=1, game="001", **changes):
    record = {
        "SEASON_ID": "21946", "PLAYER_ID": player, "GAME_ID": game,
        "GAME_DATE": "1946-11-01", "MIN": 30, "PTS": 10,
        "REB": None, "AST": None, "STL": None, "BLK": None, "TOV": None,
    }
    record.update(changes)
    return record


class IngestionTests(unittest.TestCase):
    def test_season_validation(self):
        self.assertEqual(validate_season("1946-47"), "1946-47")
        self.assertEqual(validate_season("2026-27"), "2026-27")
        with self.assertRaises(ValueError):
            validate_season("2024-26")

    def test_missing_is_not_zero(self):
        report = validate_rows([row()], "1946-47")
        self.assertEqual(report["missing_counts"]["STL"], 1)
        self.assertEqual(report["missing_counts"]["PTS"], 0)

    def test_duplicate_and_minutes(self):
        report = validate_rows([row(), row(MIN=80)], "1946-47")
        self.assertEqual(report["duplicate_player_game_rows"], 1)
        self.assertEqual(report["invalid_minutes"], 1)

    def test_cache_skips_fetch_and_preserves_nulls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            calls = []
            def fetch(season):
                calls.append(season)
                return [row()]
            first = ingest("1946-47", root, fetcher=fetch)
            second = ingest("1946-47", root, fetcher=lambda _: self.fail("unexpected network"))
            self.assertEqual(calls, ["1946-47"])
            self.assertEqual(first["source"], "nba_api")
            self.assertEqual(second["source"], "cache")
            self.assertIsNone(json.loads((root / "raw" / "1946-47.json").read_text())[0]["STL"])
            self.assertTrue((root / "reports" / "1946-47.json").exists())

    def test_duplicate_conflict_preserved_in_raw_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = [row(player=77671, game="0024600076", TEAM_ABBREVIATION="PHW"),
                    row(player=77671, game="0024600076", TEAM_ABBREVIATION="NYK")]
            report = ingest("1946-47", root, fetcher=lambda _: rows)
            self.assertEqual(report["duplicate_player_game_rows"], 1)
            self.assertEqual(len(report["duplicate_conflict_rows"]), 2)
            self.assertEqual(len(json.loads((root / "raw" / "1946-47.json").read_text())), 2)

    def test_bad_data_is_not_cached(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                ingest("1946-47", root, fetcher=lambda _: [row(MIN=-5)])
            self.assertFalse((root / "raw" / "1946-47.json").exists())

    def test_report_matches_cached_records_on_rerun(self):
        rows = [row(), row(PTS=12), row(player=2, REB=0, AST=2),
                row(player=3, REB=5)]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = ingest("1946-47", root, fetcher=lambda _: rows)
            second = ingest("1946-47", root, fetcher=lambda _: self.fail("unexpected network"))
            cached = json.loads((root / "raw" / "1946-47.json").read_text())
            saved = json.loads((root / "reports" / "1946-47.json").read_text())
            self.assertEqual(saved, second)
            self.assertEqual({**first, "source": "cache"}, second)
            self.assertEqual(second["rows"], len(cached))
            self.assertEqual(second["missing_counts"]["REB"], 2)
            self.assertEqual(second["missing_percent"]["REB"], 50.0)
            self.assertEqual(second["missing_percent"]["AST"], 75.0)
            self.assertEqual(second["duplicate_player_game_rows"], 1)
            self.assertEqual(len(second["duplicate_conflict_rows"]), 2)
            self.assertEqual(len(exclude_unresolved_duplicates(cached)), 2)

    def test_excludes_entire_duplicate_groups_without_changing_raw(self):
        rows = [row(player=1), row(player=2, TEAM_ABBREVIATION="PHW"),
                row(player=2, TEAM_ABBREVIATION="NYK"), row(player=2, PTS=20),
                row(player=3), row(player=3), row(player=1, game="002")]
        original = json.loads(json.dumps(rows))
        derived = exclude_unresolved_duplicates(rows)
        self.assertEqual(derived, [rows[0], rows[-1]])
        self.assertEqual(rows, original)
        self.assertEqual(validate_rows(derived, "1946-47")["duplicate_player_game_rows"], 0)
        derived[0]["PTS"] = 99
        self.assertEqual(rows, original)

    def test_duplicate_exclusion_handles_empty_input(self):
        self.assertEqual(exclude_unresolved_duplicates([]), [])

class HistoricalBatchTests(unittest.TestCase):
    def test_range_and_bounds(self):
        self.assertEqual((len(season_range()), season_range()[0], season_range()[-1]),
                         (80, "1946-47", "2025-26"))
        for season in ("1945-46", "2027-28", "1999-01"):
            with self.assertRaises(ValueError):
                validate_season(season)
        with self.assertRaises(ValueError):
            season_range("2025-26", "1946-47")

    def test_read_only_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ingest("1946-47", root, fetcher=lambda _: [row()])
            before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = run_batch(season_range(), root, dry_run=True, fetcher=lambda _: self.fail("network"))
            self.assertEqual(result["selected"], season_range("1947-48", "1951-52"))
            self.assertEqual(result["cached"], ["1946-47"])
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob("*") if p.is_file()})

    def test_interrupt_resume_and_transient_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def interrupted(season):
                if season == "1947-48":
                    raise KeyboardInterrupt()
                return [row()]
            with self.assertRaises(KeyboardInterrupt):
                run_batch(season_range("1946-47", "1948-49"), root, fetcher=interrupted, sleep=lambda _: None)
            original = (root / "raw/1946-47.json").read_bytes()
            calls, waits = [], []
            def retry(season):
                calls.append(season)
                if len(calls) == 1:
                    raise TimeoutError("transient")
                return [row(SEASON_ID=f"2{season[:4]}")]
            result = run_batch(season_range("1946-47", "1948-49"), root, fetcher=retry, sleep=waits.append)
            self.assertEqual(calls, ["1947-48", "1947-48", "1948-49"])
            self.assertEqual(result["completed"], ["1947-48", "1948-49"])
            self.assertEqual(waits, [2, 2])
            self.assertEqual(original, (root / "raw/1946-47.json").read_bytes())

    def test_failure_report_and_retry_next_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def failed(_):
                raise ConnectionError("fixture")
            result = run_batch(["1946-47"], root, fetcher=failed, attempts=2, sleep=lambda _: None)
            self.assertIn("2 attempts", result["failed"]["1946-47"])
            self.assertFalse((root / "raw/1946-47.json").exists())
            self.assertEqual(json.loads(next((root / "reports").glob("batch-*.json")).read_text()), result)
            self.assertEqual(run_batch(["1946-47"], root, fetcher=lambda _: [row()])["completed"], ["1946-47"])

    def test_corrupt_cache_and_explicit_refresh_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "raw").mkdir()
            path = root / "raw/1946-47.json"
            path.write_text("invalid JSON")
            result = run_batch(["1946-47"], root, fetcher=lambda _: self.fail("network"))
            self.assertIn("1946-47", result["failed"])
            self.assertEqual(path.read_text(), "invalid JSON")
            ingest("1946-47", root, refresh=True, fetcher=lambda _: [row()])
            self.assertEqual(next((root / "raw/backups").glob("*.json")).read_text(), "invalid JSON")
            self.assertIsNone(json.loads(path.read_text())[0]["STL"])
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                ingest("1946-47", root, refresh=True, fetcher=lambda _: [row(MIN=-1)])
            self.assertEqual(original, path.read_bytes())
            self.assertEqual(json.loads((root / "reports/1946-47.json").read_text())["invalid_minutes"], 1)

    def test_schema_season_and_batch_limits(self):
        bad = row()
        del bad["AST"]
        for records in ([row(), bad], {"error": "server response"}, [None], []):
            with self.assertRaises(ValueError):
                validate_rows(records, "1946-47")
        self.assertIn("wrong regular season", validate_rows([row(SEASON_ID="21947")], "1946-47")["warnings"])
        with tempfile.TemporaryDirectory() as temp:
            calls = []
            def fetch(season):
                calls.append(season)
                return [row(SEASON_ID=f"2{season[:4]}")]
            result = run_batch(season_range(), Path(temp), batch_size=2, fetcher=fetch, sleep=lambda _: None)
            self.assertEqual(calls, ["1946-47", "1947-48"])
            self.assertEqual(result["remaining_after_selection"], 78)
            for kwargs in ({"batch_size": 0}, {"attempts": 0}, {"delay": -1}, {"backoff": float("nan")}):
                with self.assertRaises(ValueError):
                    run_batch([], Path(temp), **kwargs)


if __name__ == "__main__":
    unittest.main()
