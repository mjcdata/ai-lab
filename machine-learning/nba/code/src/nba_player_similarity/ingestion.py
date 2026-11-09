"""Resumable, local-only NBA regular-season ingestion.

No network access occurs on import. Live requests are opt-in through the CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

SEASON_RE = re.compile(r"^(19|20)\d{2}-\d{2}$")
REQUIRED = ("SEASON_ID", "PLAYER_ID", "GAME_ID", "GAME_DATE", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV")
STATS = ("MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV")
PILOT = ("1946-47", "1977-78", "2024-25")


def validate_season(season: str) -> str:
    if not SEASON_RE.fullmatch(season) or int(season[-2:]) != (int(season[:4]) + 1) % 100:
        raise ValueError(f"Invalid NBA season: {season!r}; expected YYYY-YY")
    if not 1946 <= int(season[:4]) <= 2026:
        raise ValueError("Supported seasons: 1946-47 through 2026-27 (history defaults through 2025-26)")
    return season


def season_range(start="1946-47", end="2025-26") -> list[str]:
    validate_season(start)
    validate_season(end)
    if start > end:
        raise ValueError("Start season must precede end season")
    return [f"{year}-{(year + 1) % 100:02d}" for year in range(int(start[:4]), int(end[:4]) + 1)]


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
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{season}: expected a list of row objects")
    columns = set.intersection(*(set(row) for row in rows))
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
    invalid_seasons = sum(str(row.get("SEASON_ID")) != f"2{season[:4]}" for row in rows)
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
        "wrong_season_rows": invalid_seasons,
        "warnings": [
            label for label, count in (
                ("missing identifiers", invalid_ids), ("wrong regular season", invalid_seasons),
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


def ingest(season: str, root: Path, *, fetcher=fetch_season, refresh: bool = False,
           attempts: int = 3, backoff: float = 2, sleep=time.sleep) -> dict:
    validate_season(season)
    if attempts < 1 or not math.isfinite(backoff) or backoff < 0:
        raise ValueError("Attempts must be positive and backoff finite/nonnegative")
    raw_path = root / "raw" / f"{season}.json"
    report_path = root / "reports" / f"{season}.json"
    cached = raw_path.exists() and not refresh
    if cached:
        rows = json.loads(raw_path.read_text(encoding="utf-8"))
    else:
        for attempt in range(attempts):
            try:
                rows = fetcher(season)
                break
            except ImportError:
                raise  # Missing optional dependencies are not transient.
            except Exception as exc:
                if attempt + 1 == attempts:
                    raise RuntimeError(f"{season}: fetch failed after {attempts} attempts: {exc}") from exc
                sleep(min(60, backoff * 2 ** min(attempt, 6)))
    report = validate_rows(rows, season)
    report["source"] = "cache" if cached else "nba_api"
    _atomic_json(report_path, report)
    if report["warnings"]:
        raise ValueError(f"{season}: structural validation failed: {report['warnings']}")
    if not cached:
        # Explicit refresh retains original bytes, including an invalid old cache.
        if raw_path.exists():
            original = raw_path.read_bytes()
            digest = hashlib.sha256(original).hexdigest()
            backup = root / "raw" / "backups" / f"{season}.{digest}.json"
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                with backup.open("xb") as file:
                    file.write(original)
            if backup.read_bytes() != original:
                raise OSError(f"Incomplete backup at {backup}; original cache preserved")
        _atomic_json(raw_path, rows)
    return report


def run_batch(seasons: list[str], root: Path, *, batch_size: int = 5,
              fetcher=fetch_season, attempts: int = 3, backoff: float = 2,
              delay: float = 2, sleep=time.sleep, dry_run: bool = False,
              refresh: bool = False) -> dict:
    """Revalidate caches, then attempt at most batch_size missing seasons.

    Each successful season is independently durable. Rerunning resumes without
    needing the batch report, including after Ctrl-C or a lost report write.
    Invalid existing caches are reported and preserved, never silently replaced.
    """
    if batch_size < 1 or attempts < 1 or any(not math.isfinite(x) or x < 0 for x in (delay, backoff)):
        raise ValueError("Batch size/attempts must be positive; delays finite/nonnegative")
    seasons = list(dict.fromkeys(validate_season(s) for s in seasons))
    summary = {"started_at": datetime.now(timezone.utc).isoformat(),
               "dry_run": dry_run, "cached": [], "selected": [], "completed": [], "failed": {}}
    pending = []
    for season in seasons:
        path = root / "raw" / f"{season}.json"
        if path.exists() and not refresh:
            try:
                rows = json.loads(path.read_text(encoding="utf-8"))
                report = validate_rows(rows, season)
                if report["warnings"]:
                    raise ValueError(str(report["warnings"]))
                if not dry_run:
                    _atomic_json(root / "reports" / f"{season}.json", {**report, "source": "cache"})
                summary["cached"].append(season)
            except (ValueError, OSError) as exc:
                summary["failed"][season] = f"Existing cache preserved; inspect or explicitly --refresh: {exc}"
        else:
            pending.append(season)
    summary["selected"] = pending[:batch_size]
    summary["remaining_after_selection"] = len(pending) - len(summary["selected"])
    if dry_run:
        return summary
    report_path = root / "reports" / f"batch-{uuid4().hex}.json"
    _atomic_json(report_path, summary)
    for index, season in enumerate(summary["selected"]):
        if index:
            sleep(delay)
        try:
            ingest(season, root, fetcher=fetcher, refresh=refresh,
                   attempts=attempts, backoff=backoff, sleep=sleep)
            summary["completed"].append(season)
        except (ValueError, OSError, RuntimeError, ImportError) as exc:
            summary["failed"][season] = str(exc)
        _atomic_json(report_path, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local historical NBA regular-season ingestion")
    parser.add_argument("seasons", nargs="*", help="Explicit YYYY-YY seasons; otherwise use inclusive range")
    parser.add_argument("--start-season", default="1946-47")
    parser.add_argument("--end-season", default="2025-26")
    parser.add_argument("--batch-size", type=int, default=5, help="Maximum season fetches per invocation")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--backoff", type=float, default=2)
    parser.add_argument("--delay", type=float, default=2, help="Seconds between season fetches")
    parser.add_argument("--download", action="store_true", help="Opt into network requests; default is read-only inventory")
    parser.add_argument("--refresh", action="store_true", help="Explicitly re-fetch, backing up any existing raw bytes")
    args = parser.parse_args(argv)
    try:
        summary = run_batch(args.seasons or season_range(args.start_season, args.end_season),
                            args.data_dir, batch_size=args.batch_size, attempts=args.attempts,
                            backoff=args.backoff, delay=args.delay,
                            dry_run=not args.download, refresh=args.refresh)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
