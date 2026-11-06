"""Small, local-only NBA season ingestion pilot.

No network access occurs on import. Live requests are opt-in through the CLI.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import tempfile
from collections import Counter
from pathlib import Path

SEASON_RE = re.compile(r"^(19|20)\d{2}-\d{2}$")
REQUIRED = ("SEASON_ID", "PLAYER_ID", "GAME_ID", "GAME_DATE", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV")
STATS = ("MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV")
PILOT = ("1946-47", "1977-78", "2024-25")


def validate_season(season: str) -> str:
    if not SEASON_RE.fullmatch(season) or int(season[-2:]) != (int(season[:4]) + 1) % 100:
        raise ValueError(f"Invalid NBA season: {season!r}; expected YYYY-YY")
    return season


def _missing(value: object) -> bool:
    return value is None or value == "" or (isinstance(value, float) and math.isnan(value))


def _number(value: object) -> float | None:
    if _missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def exclude_unresolved_duplicates(rows: list[dict]) -> list[dict]:
    """Return only unique player/game groups; leave raw records unchanged.

    Future derived datasets must apply this safeguard before aggregating.
    Even identical duplicate rows remain unresolved until independently reviewed.
    This is not a substitute for identifier or historical coverage validation.
    """
    keys = [(str(row.get("PLAYER_ID")), str(row.get("GAME_ID"))) for row in rows]
    counts = Counter(keys)
    return [row.copy() for row, key in zip(rows, keys) if counts[key] == 1]


def validate_rows(rows: list[dict], season: str) -> dict:
    """Report missingness and structural issues without filling historical nulls."""
    if not rows:
        raise ValueError(f"{season}: empty API response")
    columns = set(rows[0])
    absent = sorted(set(REQUIRED) - columns)
    if absent:
        raise ValueError(f"{season}: missing required columns: {absent}")
    missing = {key: sum(_missing(row.get(key)) for row in rows) for key in STATS}
    invalid_ids = sum(_missing(row.get("PLAYER_ID")) or _missing(row.get("GAME_ID")) for row in rows)
    invalid_minutes = sum(
        not _missing(row.get("MIN")) and (
            _number(row.get("MIN")) is None or not 0 <= _number(row.get("MIN")) <= 70
        ) for row in rows
    )
    invalid_points = sum(
        not _missing(row.get("PTS")) and (
            _number(row.get("PTS")) is None or _number(row.get("PTS")) < 0
        ) for row in rows
    )
    keys = [(str(row.get("PLAYER_ID")), str(row.get("GAME_ID"))) for row in rows]
    duplicates = sum(n - 1 for n in Counter(keys).values() if n > 1)
    conflict_keys = {key for key, n in Counter(keys).items() if n > 1}
    conflict_rows = [
        {"PLAYER_ID": row.get("PLAYER_ID"), "GAME_ID": row.get("GAME_ID"),
         "GAME_DATE": row.get("GAME_DATE"), "TEAM_ABBREVIATION": row.get("TEAM_ABBREVIATION"),
         "MIN": row.get("MIN"), "PTS": row.get("PTS")}
        for row in rows
        if (str(row.get("PLAYER_ID")), str(row.get("GAME_ID"))) in conflict_keys
    ]
    return {
        "season": season, "rows": len(rows), "columns": sorted(columns),
        "missing_counts": missing, "missing_percent": {
            key: round(100 * count / len(rows), 2) for key, count in missing.items()
        },
        "missing_identifiers": invalid_ids, "duplicate_player_game_rows": duplicates, "duplicate_conflict_rows": conflict_rows,
        "invalid_minutes": invalid_minutes, "invalid_points": invalid_points,
        "warnings": [
            label for label, count in (
                ("missing identifiers", invalid_ids),
                ("implausible minutes", invalid_minutes), ("invalid points", invalid_points)
            ) if count
        ],
    }


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            json.dump(payload, file, indent=2, allow_nan=False)
            file.write("\n")
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, path)


def _normalize(rows: list[dict]) -> list[dict]:
    """Convert pandas/numpy scalar nulls into JSON-safe native values."""
    import pandas as pd
    clean = pd.DataFrame(rows).astype(object).where(lambda frame: pd.notna(frame), None)
    return clean.to_dict(orient="records")


def fetch_season(season: str) -> list[dict]:
    """Live NBA request: call only from a user-initiated local command."""
    from nba_api.stats.endpoints import leaguegamelog
    frame = leaguegamelog.LeagueGameLog(
        season=season, player_or_team_abbreviation="P", season_type_all_star="Regular Season",
        timeout=20,
    ).get_data_frames()[0]
    return _normalize(frame.to_dict(orient="records"))


def ingest(season: str, root: Path, *, fetcher=fetch_season, refresh: bool = False) -> dict:
    validate_season(season)
    raw_path = root / "raw" / f"{season}.json"
    report_path = root / "reports" / f"{season}.json"
    if raw_path.exists() and not refresh:
        with raw_path.open(encoding="utf-8") as file:
            rows = json.load(file)
        report = validate_rows(rows, season)
        report["source"] = "cache"
    else:
        rows = fetcher(season)
        report = validate_rows(rows, season)
        if report["warnings"]:
            raise ValueError(f"{season}: structural validation failed: {report['warnings']}")
        _atomic_json(raw_path, rows)
        report["source"] = "nba_api"
    if report["warnings"]:
        raise ValueError(f"{season}: cached data failed validation: {report['warnings']}")
    _atomic_json(report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local NBA historical ingestion pilot")
    parser.add_argument("seasons", nargs="*", default=list(PILOT), help="YYYY-YY; default: pilot seasons")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="local output directory")
    parser.add_argument("--refresh", action="store_true", help="re-fetch existing seasons")
    args = parser.parse_args(argv)
    for season in args.seasons:
        try:
            report = ingest(season, args.data_dir, refresh=args.refresh)
        except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
            parser.exit(1, f"{season}: {exc}\n")
        print(f"{season}: {report['rows']} records ({report['source']}); missing: {report['missing_percent']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
