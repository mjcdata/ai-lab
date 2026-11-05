"""Offline pilot tests; no requests to stats.nba.com."""
import json
import tempfile
import unittest
from pathlib import Path
from nba_player_similarity.ingestion import ingest, validate_rows, validate_season


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

    def test_bad_data_is_not_cached(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                ingest("1946-47", root, fetcher=lambda _: [row(MIN=-5)])
            self.assertFalse((root / "raw" / "1946-47.json").exists())


if __name__ == "__main__":
    unittest.main()
