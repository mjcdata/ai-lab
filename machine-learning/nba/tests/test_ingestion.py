"""Offline pilot tests; no requests to stats.nba.com."""
import json
import tempfile
import unittest
from pathlib import Path
from nba_player_similarity.ingestion import (
    exclude_unresolved_duplicates, ingest, validate_rows, validate_season,
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


if __name__ == "__main__":
    unittest.main()
