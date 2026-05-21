"""SQLite schema and helpers for StatSense."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "statsense.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    competition TEXT NOT NULL,
    season TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS player_stats (
    player_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    position TEXT,
    goals REAL DEFAULT 0,
    assists REAL DEFAULT 0,
    xg REAL DEFAULT 0,
    xa REAL DEFAULT 0,
    pass_accuracy_pct REAL,
    key_passes INTEGER DEFAULT 0,
    progressive_passes INTEGER DEFAULT 0,
    distance_covered_km REAL,
    duels_won_pct REAL,
    shot_accuracy_pct REAL,
    conversion_rate_pct REAL,
    PRIMARY KEY (player_id, match_id),
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS team_stats (
    match_id INTEGER NOT NULL,
    team TEXT NOT NULL,
    possession_pct REAL,
    shots_on_target INTEGER DEFAULT 0,
    ppda REAL,
    xg_for REAL DEFAULT 0,
    xg_against REAL DEFAULT 0,
    formation TEXT,
    pressing_intensity REAL,
    total_shots INTEGER DEFAULT 0,
    key_passes INTEGER DEFAULT 0,
    PRIMARY KEY (match_id, team),
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS match_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    minute INTEGER NOT NULL DEFAULT 0,
    period INTEGER DEFAULT 1,
    event_type TEXT NOT NULL,
    team TEXT,
    player_name TEXT,
    player_id INTEGER,
    detail TEXT,
    related_player TEXT,
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE INDEX IF NOT EXISTS idx_match_events_match ON match_events(match_id, minute);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def upsert_match(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO matches (
            match_id, date, home_team, away_team, home_score, away_score,
            competition, season
        ) VALUES (
            :match_id, :date, :home_team, :away_team, :home_score, :away_score,
            :competition, :season
        )
        ON CONFLICT(match_id) DO UPDATE SET
            date = excluded.date,
            home_team = excluded.home_team,
            away_team = excluded.away_team,
            home_score = excluded.home_score,
            away_score = excluded.away_score,
            competition = excluded.competition,
            season = excluded.season
        """,
        row,
    )


def upsert_player_stats(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO player_stats (
            player_id, match_id, player_name, team, position,
            goals, assists, xg, xa, pass_accuracy_pct, key_passes,
            progressive_passes, distance_covered_km, duels_won_pct,
            shot_accuracy_pct, conversion_rate_pct
        ) VALUES (
            :player_id, :match_id, :player_name, :team, :position,
            :goals, :assists, :xg, :xa, :pass_accuracy_pct, :key_passes,
            :progressive_passes, :distance_covered_km, :duels_won_pct,
            :shot_accuracy_pct, :conversion_rate_pct
        )
        ON CONFLICT(player_id, match_id) DO UPDATE SET
            player_name = excluded.player_name,
            team = excluded.team,
            position = excluded.position,
            goals = excluded.goals,
            assists = excluded.assists,
            xg = excluded.xg,
            xa = excluded.xa,
            pass_accuracy_pct = excluded.pass_accuracy_pct,
            key_passes = excluded.key_passes,
            progressive_passes = excluded.progressive_passes,
            distance_covered_km = excluded.distance_covered_km,
            duels_won_pct = excluded.duels_won_pct,
            shot_accuracy_pct = excluded.shot_accuracy_pct,
            conversion_rate_pct = excluded.conversion_rate_pct
        """,
        rows,
    )


def replace_match_events(conn: sqlite3.Connection, match_id: int, rows: list[dict[str, Any]]) -> None:
    conn.execute("DELETE FROM match_events WHERE match_id = ?", (match_id,))
    if not rows:
        return
    for row in rows:
        row["match_id"] = match_id
    conn.executemany(
        """
        INSERT INTO match_events (
            match_id, minute, period, event_type, team, player_name,
            player_id, detail, related_player
        ) VALUES (
            :match_id, :minute, :period, :event_type, :team, :player_name,
            :player_id, :detail, :related_player
        )
        """,
        rows,
    )


def get_match_events(conn: sqlite3.Connection, match_id: int) -> list[dict[str, Any]]:
    return rows_to_dicts(
        conn.execute(
            """
            SELECT event_id, match_id, minute, period, event_type, team,
                   player_name, player_id, detail, related_player
            FROM match_events
            WHERE match_id = ?
            ORDER BY minute ASC, event_id ASC
            """,
            (match_id,),
        ).fetchall()
    )


def get_match_event(
    conn: sqlite3.Connection, match_id: int, event_id: int
) -> dict[str, Any] | None:
    return row_to_dict(
        conn.execute(
            """
            SELECT * FROM match_events
            WHERE match_id = ? AND event_id = ?
            """,
            (match_id, event_id),
        ).fetchone()
    )


def upsert_team_stats(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO team_stats (
            match_id, team, possession_pct, shots_on_target, ppda,
            xg_for, xg_against, formation, pressing_intensity,
            total_shots, key_passes
        ) VALUES (
            :match_id, :team, :possession_pct, :shots_on_target, :ppda,
            :xg_for, :xg_against, :formation, :pressing_intensity,
            :total_shots, :key_passes
        )
        ON CONFLICT(match_id, team) DO UPDATE SET
            possession_pct = excluded.possession_pct,
            shots_on_target = excluded.shots_on_target,
            ppda = excluded.ppda,
            xg_for = excluded.xg_for,
            xg_against = excluded.xg_against,
            formation = excluded.formation,
            pressing_intensity = excluded.pressing_intensity,
            total_shots = excluded.total_shots,
            key_passes = excluded.key_passes
        """,
        rows,
    )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def list_matches(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return rows_to_dicts(
        conn.execute(
            """
            SELECT match_id, date, home_team, away_team, home_score, away_score,
                   competition, season
            FROM matches
            ORDER BY date DESC, match_id DESC
            """
        ).fetchall()
    )


def get_match(conn: sqlite3.Connection, match_id: int) -> dict[str, Any] | None:
    return row_to_dict(
        conn.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,)).fetchone()
    )


def get_team_stats_for_match(
    conn: sqlite3.Connection, match_id: int
) -> list[dict[str, Any]]:
    return rows_to_dicts(
        conn.execute(
            "SELECT * FROM team_stats WHERE match_id = ? ORDER BY team",
            (match_id,),
        ).fetchall()
    )


def get_player_stats_for_match(
    conn: sqlite3.Connection, match_id: int
) -> list[dict[str, Any]]:
    return rows_to_dicts(
        conn.execute(
            """
            SELECT * FROM player_stats
            WHERE match_id = ? AND team != 'Unknown'
            ORDER BY xg DESC, goals DESC
            """,
            (match_id,),
        ).fetchall()
    )


def get_player_match_row(
    conn: sqlite3.Connection, match_id: int, player_id: int
) -> dict[str, Any] | None:
    return row_to_dict(
        conn.execute(
            """
            SELECT * FROM player_stats
            WHERE match_id = ? AND player_id = ?
            """,
            (match_id, player_id),
        ).fetchone()
    )


def get_match_player_averages(
    conn: sqlite3.Connection, match_id: int
) -> dict[str, float]:
    """Per-stat averages across all players in the match (benchmarks)."""
    row = conn.execute(
        """
        SELECT
            AVG(goals) AS goals,
            AVG(assists) AS assists,
            AVG(xg) AS xg,
            AVG(xa) AS xa,
            AVG(pass_accuracy_pct) AS pass_accuracy_pct,
            AVG(key_passes) AS key_passes,
            AVG(progressive_passes) AS progressive_passes,
            AVG(duels_won_pct) AS duels_won_pct,
            AVG(shot_accuracy_pct) AS shot_accuracy_pct,
            AVG(conversion_rate_pct) AS conversion_rate_pct
        FROM player_stats
        WHERE match_id = ? AND team != 'Unknown'
        """,
        (match_id,),
    ).fetchone()
    if not row:
        return {}
    return {
        k: round(float(v), 3) if v is not None else 0.0
        for k, v in dict(row).items()
    }


def get_team_stat_averages(conn: sqlite3.Connection) -> dict[str, float]:
    """Database-wide team stat averages for benchmarks."""
    row = conn.execute(
        """
        SELECT
            AVG(possession_pct) AS possession_pct,
            AVG(shots_on_target) AS shots_on_target,
            AVG(ppda) AS ppda,
            AVG(xg_for) AS xg_for,
            AVG(xg_against) AS xg_against,
            AVG(pressing_intensity) AS pressing_intensity
        FROM team_stats
        """
    ).fetchone()
    if not row:
        return {}
    return {
        k: round(float(v), 3) if v is not None else 0.0
        for k, v in dict(row).items()
    }


def get_player_season_stats(
    conn: sqlite3.Connection, player_id: int
) -> list[dict[str, Any]]:
    """Per-match rows for a player across all loaded matches."""
    return rows_to_dicts(
        conn.execute(
            """
            SELECT
                ps.*,
                m.date AS match_date,
                m.home_team,
                m.away_team,
                m.home_score,
                m.away_score,
                m.competition,
                m.season
            FROM player_stats ps
            JOIN matches m ON m.match_id = ps.match_id
            WHERE ps.player_id = ?
            ORDER BY m.date ASC
            """,
            (player_id,),
        ).fetchall()
    )


def aggregate_player_season(
    matches: list[dict[str, Any]],
) -> dict[str, Any]:
    """Sum/average player metrics across season matches."""
    if not matches:
        return {}
    n = len(matches)
    totals = {
        "matches_played": n,
        "goals": sum(m.get("goals") or 0 for m in matches),
        "assists": sum(m.get("assists") or 0 for m in matches),
        "xg": round(sum(m.get("xg") or 0 for m in matches), 3),
        "xa": round(sum(m.get("xa") or 0 for m in matches), 3),
        "key_passes": sum(m.get("key_passes") or 0 for m in matches),
        "progressive_passes": sum(m.get("progressive_passes") or 0 for m in matches),
    }
    pct_fields = ["pass_accuracy_pct", "duels_won_pct", "shot_accuracy_pct", "conversion_rate_pct"]
    for field in pct_fields:
        vals = [m[field] for m in matches if m.get(field) is not None]
        totals[f"avg_{field}"] = round(sum(vals) / len(vals), 1) if vals else None
    totals["avg_xg_per_match"] = round(totals["xg"] / n, 3)
    totals["avg_goals_per_match"] = round(totals["goals"] / n, 2)
    return totals
