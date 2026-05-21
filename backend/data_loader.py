"""
Fetch and parse StatsBomb open data into StatSense SQLite tables.

Competitions loaded (sample): La Liga, Premier League, FIFA Women's World Cup.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from statsbombpy import sb

from database import (
    DEFAULT_DB_PATH,
    get_connection,
    init_db,
    replace_match_events,
    upsert_match,
    upsert_player_stats,
    upsert_team_stats,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Open-data competition targets: (competition_id, season_id, display season)
TARGET_COMPETITIONS = [
    (11, 42, "La Liga 2019/2020"),
    (2, 27, "Premier League 2015/2016"),
    (72, 30, "FIFA Women's World Cup 2019"),
]

PITCH_LENGTH = 120.0
ATTACKING_THIRD_X = 80.0
PROGRESSIVE_PASS_MIN_YARDS = 10.0

SHOT_ON_TARGET = {"Goal", "Saved", "Saved to Post"}


def _col_bool(df: pd.DataFrame, column: str) -> pd.Series:
    """Safe boolean column access (older open-data matches may omit fields)."""
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    return df[column].eq(True)


def _loc_x(series: pd.Series) -> pd.Series:
    """Extract x coordinate from StatsBomb location lists."""
    return series.apply(
        lambda v: float(v[0]) if isinstance(v, (list, tuple)) and len(v) >= 1 else np.nan
    )


def _formation_string(tactics: Any) -> str | None:
    if not isinstance(tactics, dict):
        return None
    formation = tactics.get("formation")
    if formation is None:
        return None
    s = str(formation)
    if s.isdigit() and len(s) >= 3:
        return "-".join(list(s))
    return s


def _primary_position(positions: Any) -> str | None:
    if not isinstance(positions, list) or not positions:
        return None
    first = positions[0]
    if isinstance(first, dict):
        return first.get("position")
    return None


def _build_lineup_lookup(lineups: dict[str, pd.DataFrame]) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for team_name, df in lineups.items():
        for _, row in df.iterrows():
            pid = int(row["player_id"])
            lookup[pid] = {
                "player_name": row.get("player_name") or row.get("player_nickname"),
                "team": team_name,
                "position": _primary_position(row.get("positions")),
            }
    return lookup


def _player_label(row: pd.Series, lineup_lookup: dict[int, dict]) -> tuple[str | None, int | None]:
    pid = row.get("player_id")
    if pd.notna(pid):
        pid = int(pid)
        info = lineup_lookup.get(pid, {})
        name = row.get("player_name") or info.get("player_name")
        if name:
            return str(name), pid
    name = row.get("player_name")
    if name and pd.notna(name):
        return str(name), int(pid) if pd.notna(pid) else None
    return None, None


def _parse_timeline_events(
    events: pd.DataFrame, lineup_lookup: dict[int, dict]
) -> list[dict[str, Any]]:
    """Extract goals, cards, and substitutions for the match timeline."""
    rows: list[dict[str, Any]] = []
    ev = events.copy()
    ev["minute"] = pd.to_numeric(ev.get("minute"), errors="coerce").fillna(0).astype(int)
    ev["period"] = pd.to_numeric(ev.get("period"), errors="coerce").fillna(1).astype(int)

    shots = ev[ev["type"] == "Shot"]
    if not shots.empty:
        if "shot_outcome" in shots.columns:
            goals = shots[shots["shot_outcome"] == "Goal"]
        else:
            goals = shots[_col_bool(shots, "goal")]
        for _, row in goals.iterrows():
            name, pid = _player_label(row, lineup_lookup)
            assist = row.get("pass_player_name") or row.get("pass_recipient_name")
            if pd.isna(assist):
                assist = None
            rows.append(
                {
                    "minute": int(row["minute"]),
                    "period": int(row["period"]),
                    "event_type": "goal",
                    "team": row.get("team"),
                    "player_name": name,
                    "player_id": pid,
                    "detail": "Goal",
                    "related_player": str(assist) if assist else None,
                }
            )

    subs = ev[ev["type"] == "Substitution"]
    for _, row in subs.iterrows():
        name, pid = _player_label(row, lineup_lookup)
        replacement = row.get("substitution_replacement_name")
        if pd.isna(replacement):
            replacement = None
        rows.append(
            {
                "minute": int(row["minute"]),
                "period": int(row["period"]),
                "event_type": "substitution",
                "team": row.get("team"),
                "player_name": name,
                "player_id": pid,
                "detail": "Substitution",
                "related_player": str(replacement) if replacement else None,
            }
        )

    fouls = ev[ev["type"] == "Foul Committed"]
    for _, row in fouls.iterrows():
        card = row.get("foul_committed_card")
        if pd.isna(card) or not card:
            if _col_bool(pd.DataFrame([row]), "yellow_card").iloc[0]:
                card = "Yellow Card"
            elif _col_bool(pd.DataFrame([row]), "red_card").iloc[0]:
                card = "Red Card"
            else:
                continue
        name, pid = _player_label(row, lineup_lookup)
        rows.append(
            {
                "minute": int(row["minute"]),
                "period": int(row["period"]),
                "event_type": "card",
                "team": row.get("team"),
                "player_name": name,
                "player_id": pid,
                "detail": str(card),
                "related_player": None,
            }
        )

    behaviour = ev[ev["type"] == "Bad Behaviour"]
    for _, row in behaviour.iterrows():
        card = row.get("bad_behaviour_card")
        if pd.isna(card) or not card:
            continue
        name, pid = _player_label(row, lineup_lookup)
        rows.append(
            {
                "minute": int(row["minute"]),
                "period": int(row["period"]),
                "event_type": "card",
                "team": row.get("team"),
                "player_name": name,
                "player_id": pid,
                "detail": str(card),
                "related_player": None,
            }
        )

    rows.sort(key=lambda r: (r["minute"], r["event_type"]))
    return rows


def _parse_player_stats(events: pd.DataFrame, lineup_lookup: dict[int, dict]) -> list[dict]:
    """Aggregate per-player metrics from match events."""
    ev = events.copy()
    ev["player_id"] = pd.to_numeric(ev["player_id"], errors="coerce")

    players = set(ev["player_id"].dropna().astype(int))
    for pid in lineup_lookup:
        players.add(pid)

    passes = ev[ev["type"] == "Pass"].copy()
    passes["start_x"] = _loc_x(passes["location"])
    passes["end_x"] = _loc_x(passes["pass_end_location"])
    passes["progressive"] = (passes["end_x"] - passes["start_x"]) >= PROGRESSIVE_PASS_MIN_YARDS
    passes["completed"] = passes["pass_outcome"].isna() | (
        passes["pass_outcome"].astype(str) == "Complete"
    )

    shots = ev[ev["type"] == "Shot"].copy()
    shots["xg"] = pd.to_numeric(shots["shot_statsbomb_xg"], errors="coerce").fillna(0)
    shots["on_target"] = shots["shot_outcome"].isin(SHOT_ON_TARGET)
    shots["goal"] = shots["shot_outcome"] == "Goal"

    duels = ev[ev["type"] == "Duel"].copy()
    duels["won"] = duels["duel_outcome"].isin({"Won", "Success In Play", "Success Out"})

    # xA: sum xG of shots created by player's key pass
    xa_by_player: dict[int, float] = {}
    if "shot_key_pass_id" in shots.columns and "id" in passes.columns:
        assisted = shots.dropna(subset=["shot_key_pass_id"]).merge(
            passes[["id", "player_id"]].rename(columns={"player_id": "assist_player_id"}),
            left_on="shot_key_pass_id",
            right_on="id",
            how="left",
        )
        for pid, grp in assisted.groupby("assist_player_id"):
            if pd.notna(pid):
                xa_by_player[int(pid)] = float(grp["xg"].sum())

    rows: list[dict] = []
    for pid in sorted(players):
        info = lineup_lookup.get(pid, {})
        p_passes = passes[passes["player_id"] == pid]
        p_shots = shots[shots["player_id"] == pid]
        p_duels = duels[duels["player_id"] == pid]

        pass_total = len(p_passes)
        pass_acc = None
        if pass_total > 0:
            pass_acc = round(100.0 * p_passes["completed"].sum() / pass_total, 1)

        shot_total = len(p_shots)
        shot_acc = None
        conv = None
        goals = int(p_shots["goal"].sum()) if shot_total else 0
        if shot_total > 0:
            on_tgt = int(p_shots["on_target"].sum())
            shot_acc = round(100.0 * on_tgt / shot_total, 1)
            conv = round(100.0 * goals / shot_total, 1)

        duel_total = len(p_duels)
        duels_won_pct = None
        if duel_total > 0:
            duels_won_pct = round(100.0 * p_duels["won"].sum() / duel_total, 1)

        p_mask = passes["player_id"] == pid
        assists = int((_col_bool(passes, "pass_goal_assist") & p_mask).sum())
        key_passes = int((_col_bool(passes, "pass_shot_assist") & p_mask).sum())

        rows.append(
            {
                "player_id": pid,
                "player_name": info.get("player_name")
                or ev.loc[ev["player_id"] == pid, "player"].dropna().iloc[0]
                if (ev["player_id"] == pid).any()
                else f"Player {pid}",
                "team": info.get("team")
                or ev.loc[ev["player_id"] == pid, "team"].dropna().iloc[0]
                if (ev["player_id"] == pid).any()
                else "Unknown",
                "position": info.get("position"),
                "goals": goals,
                "assists": assists,
                "xg": round(float(p_shots["xg"].sum()), 3),
                "xa": round(xa_by_player.get(pid, 0.0), 3),
                "pass_accuracy_pct": pass_acc,
                "key_passes": key_passes,
                "progressive_passes": int(p_passes["progressive"].sum()),
                "distance_covered_km": None,  # not in StatsBomb open event data
                "duels_won_pct": duels_won_pct,
                "shot_accuracy_pct": shot_acc,
                "conversion_rate_pct": conv,
            }
        )

    active = {int(x) for x in ev["player_id"].dropna().unique()}
    return [r for r in rows if r["player_id"] in active and r["team"] != "Unknown"]


def _defensive_actions(ev: pd.DataFrame) -> pd.DataFrame:
    """Events counted as defensive actions for PPDA."""
    types = {"Pressure", "Foul Committed", "Interception", "Block", "Duel", "Ball Recovery"}
    df = ev[ev["type"].isin(types)].copy()
    df["x"] = _loc_x(df["location"])
    return df


def _opponent_passes_in_attacking_third(
    ev: pd.DataFrame, defending_team: str, opponent: str
) -> int:
    """Opponent passes starting in the attacking third (x >= 80)."""
    passes = ev[(ev["type"] == "Pass") & (ev["team"] == opponent)].copy()
    passes["start_x"] = _loc_x(passes["location"])
    return int((passes["start_x"] >= ATTACKING_THIRD_X).sum())


def _parse_team_stats(
    events: pd.DataFrame,
    home_team: str,
    away_team: str,
    match_id: int,
) -> list[dict]:
    teams = [home_team, away_team]
    team_xg = {
        t: float(
            events.loc[
                (events["type"] == "Shot") & (events["team"] == t),
                "shot_statsbomb_xg",
            ]
            .astype(float)
            .fillna(0)
            .sum()
        )
        for t in teams
    }

    # Possession: share of distinct possession sequences
    poss = events.dropna(subset=["possession", "possession_team"])
    total_poss = poss["possession"].nunique()
    poss_share = {}
    for t in teams:
        n = poss.loc[poss["possession_team"] == t, "possession"].nunique()
        poss_share[t] = round(100.0 * n / total_poss, 1) if total_poss else None

    starting = events[events["type"] == "Starting XI"]
    formations = {
        row["team"]: _formation_string(row.get("tactics"))
        for _, row in starting.iterrows()
    }

    match_minutes = max(float(events["minute"].max()), 1.0)

    rows = []
    for team in teams:
        opponent = away_team if team == home_team else home_team
        shots = events[(events["type"] == "Shot") & (events["team"] == team)]
        sot = int(shots["shot_outcome"].isin(SHOT_ON_TARGET).sum())
        pressures = int(events[(events["type"] == "Pressure") & (events["team"] == team)].shape[0])
        pressing = round(pressures / match_minutes, 2)

        def_actions = _defensive_actions(events)
        def_actions = def_actions[def_actions["team"] == team]
        def_actions = def_actions[def_actions["x"] >= ATTACKING_THIRD_X]
        def_count = max(len(def_actions), 1)
        opp_passes = _opponent_passes_in_attacking_third(events, team, opponent)
        ppda = round(opp_passes / def_count, 2)

        team_passes = events[(events["type"] == "Pass") & (events["team"] == team)]
        key_passes = int(_col_bool(team_passes, "pass_shot_assist").sum())

        rows.append(
            {
                "match_id": match_id,
                "team": team,
                "possession_pct": poss_share.get(team),
                "shots_on_target": sot,
                "ppda": ppda,
                "xg_for": round(team_xg[team], 3),
                "xg_against": round(team_xg[opponent], 3),
                "formation": formations.get(team),
                "pressing_intensity": pressing,
                "total_shots": int(len(shots)),
                "key_passes": key_passes,
            }
        )
    return rows


def fetch_sample_match_ids(limit: int = 5) -> list[dict[str, Any]]:
    """Pick sample matches across La Liga, Premier League, and Women's World Cup."""
    samples: list[dict[str, Any]] = []
    per_comp = max(1, limit // len(TARGET_COMPETITIONS))
    remainder = limit - per_comp * len(TARGET_COMPETITIONS)

    for i, (comp_id, season_id, label) in enumerate(TARGET_COMPETITIONS):
        n = per_comp + (1 if i < remainder else 0)
        if n <= 0:
            continue
        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        comp_name = matches["competition_name"].iloc[0]
        season_name = matches["season"].iloc[0]
        for _, row in matches.head(n).iterrows():
            samples.append(
                {
                    "match_id": int(row["match_id"]),
                    "competition": comp_name,
                    "season": f"{comp_name} {season_name}",
                    "label": label,
                }
            )
        if len(samples) >= limit:
            break
    return samples[:limit]


def load_match(
    match_id: int,
    competition: str,
    season: str,
    conn: Any,
) -> None:
    logger.info("Loading match %s", match_id)
    matches_df = None
    for comp_id, season_id, _ in TARGET_COMPETITIONS:
        m = sb.matches(competition_id=comp_id, season_id=season_id)
        hit = m[m["match_id"] == match_id]
        if not hit.empty:
            matches_df = hit.iloc[0]
            break

    if matches_df is None:
        raise ValueError(f"Match {match_id} not found in target competitions")

    events = sb.events(match_id=match_id)
    lineups = sb.lineups(match_id=match_id)
    lineup_lookup = _build_lineup_lookup(lineups)

    home = matches_df["home_team"]
    away = matches_df["away_team"]
    match_row = {
        "match_id": match_id,
        "date": str(matches_df["match_date"])[:10],
        "home_team": home,
        "away_team": away,
        "home_score": int(matches_df["home_score"])
        if pd.notna(matches_df["home_score"])
        else None,
        "away_score": int(matches_df["away_score"])
        if pd.notna(matches_df["away_score"])
        else None,
        "competition": competition,
        "season": season,
    }
    upsert_match(conn, match_row)

    player_rows = _parse_player_stats(events, lineup_lookup)
    for row in player_rows:
        row["match_id"] = match_id
    upsert_player_stats(conn, player_rows)

    team_rows = _parse_team_stats(events, home, away, match_id)
    upsert_team_stats(conn, team_rows)

    timeline_rows = _parse_timeline_events(events, lineup_lookup)
    replace_match_events(conn, match_id, timeline_rows)

    conn.commit()
    logger.info(
        "Stored match %s: %s vs %s (%s players)",
        match_id,
        home,
        away,
        len(player_rows),
    )


def load_sample_data(
    db_path: Path | str | None = None,
    match_limit: int = 5,
) -> list[int]:
    """Fetch sample matches and persist to SQLite. Returns loaded match IDs."""
    conn = init_db(db_path)
    samples = fetch_sample_match_ids(limit=match_limit)
    loaded: list[int] = []
    for sample in samples:
        load_match(
            sample["match_id"],
            sample["competition"],
            sample["season"],
            conn,
        )
        loaded.append(sample["match_id"])
    conn.close()
    return loaded


def print_first_match_player_stats(
    db_path: Path | str | None = None,
    match_id: int | None = None,
) -> int:
    """Print player_stats for the first sample match (default: first loaded)."""
    conn = get_connection(db_path)
    if match_id is None:
        row = conn.execute(
            "SELECT match_id FROM matches ORDER BY rowid LIMIT 1"
        ).fetchone()
        if not row:
            print("No matches in database.")
            conn.close()
            return 0
        match_id = row["match_id"]
    match = conn.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,)).fetchone()
    rows = conn.execute(
        """
        SELECT player_name, team, position, goals, assists, xg, xa,
               pass_accuracy_pct, key_passes, progressive_passes,
               duels_won_pct, shot_accuracy_pct, conversion_rate_pct
        FROM player_stats
        WHERE match_id = ? AND team != 'Unknown'
        ORDER BY xg DESC, goals DESC
        """,
        (match_id,),
    ).fetchall()
    conn.close()

    print(f"\n=== Match {match_id}: {match['home_team']} vs {match['away_team']} ===")
    print(f"Date: {match['date']} | {match['competition']} | Score: {match['home_score']}-{match['away_score']}")
    print(f"\nPlayer stats ({len(rows)} players):\n")
    df = pd.DataFrame([dict(r) for r in rows])
    pd.set_option("display.max_rows", 50)
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))
    return match_id


def backfill_timelines(db_path: Path | str | None = None) -> None:
    """Re-fetch events from StatsBomb and populate match_events for loaded matches."""
    conn = init_db(db_path)
    match_ids = [
        r["match_id"]
        for r in conn.execute("SELECT match_id FROM matches").fetchall()
    ]
    for mid in match_ids:
        row = conn.execute(
            "SELECT competition, season FROM matches WHERE match_id = ?", (mid,)
        ).fetchone()
        if row:
            load_match(mid, row["competition"], row["season"], conn)
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load StatsBomb data into StatSense DB")
    parser.add_argument("--limit", type=int, default=5, help="Number of sample matches")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB_PATH), help="SQLite path")
    parser.add_argument(
        "--backfill-events",
        action="store_true",
        help="Refresh timeline events for matches already in the DB",
    )
    args = parser.parse_args()

    if args.backfill_events:
        backfill_timelines(db_path=args.db)
        print("Timeline events backfilled.")
        raise SystemExit(0)

    ids = load_sample_data(db_path=args.db, match_limit=args.limit)
    print(f"\nLoaded {len(ids)} matches: {ids}")
    demo_id = ids[0] if ids else None
    print_first_match_player_stats(db_path=args.db, match_id=demo_id)
