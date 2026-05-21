"""
StatSense FastAPI backend — match data + Groq-powered insights.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Generator, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import (
    DEFAULT_DB_PATH,
    aggregate_player_season,
    get_connection,
    init_db,
    get_match,
    get_match_event,
    get_match_events,
    get_match_player_averages,
    get_player_match_row,
    get_player_season_stats,
    get_player_stats_for_match,
    get_team_stat_averages,
    get_team_stats_for_match,
    list_matches,
)
from insight_engine import (
    STAT_LABELS,
    answer_fan_question,
    compare_players_verdict,
    explain_timeline_event,
    generate_insight_safe,
    generate_match_summary,
)

load_dotenv(DEFAULT_DB_PATH.parent / ".env")

init_db()

app = FastAPI(
    title="StatSense API",
    description="Fan-friendly sports analytics powered by StatsBomb + Groq",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PLAYER_METRICS = [
    "goals",
    "assists",
    "xg",
    "xa",
    "pass_accuracy_pct",
    "key_passes",
    "progressive_passes",
    "duels_won_pct",
    "shot_accuracy_pct",
    "conversion_rate_pct",
]

TEAM_METRICS = [
    "possession_pct",
    "shots_on_target",
    "ppda",
    "xg_for",
    "xg_against",
    "pressing_intensity",
]

LOWER_IS_BETTER = {"ppda", "xg_against"}


@contextmanager
def db() -> Generator[Any, None, None]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    match_id: int


class AskResponse(BaseModel):
    question: str
    answer: str
    match_id: int


class CompareRequest(BaseModel):
    player_a_id: int
    player_b_id: int


class CompareResponse(BaseModel):
    player_a: dict[str, Any]
    player_b: dict[str, Any]
    stats: list[dict[str, Any]]
    verdict: str


class ExplainEventRequest(BaseModel):
    event_id: int


def _match_title(m: dict[str, Any]) -> str:
    return f"{m['home_team']} vs {m['away_team']}"


def performance_badge(
    value: float | int | None,
    benchmark: float | None,
    *,
    stat_type: str,
) -> Literal["above", "below", "average"]:
    if value is None or benchmark is None:
        return "average"
    if benchmark == 0:
        return "above" if value > 0 else "average"
    higher_better = stat_type not in LOWER_IS_BETTER
    ratio = float(value) / float(benchmark)
    if higher_better:
        if ratio >= 1.15:
            return "above"
        if ratio <= 0.85:
            return "below"
        return "average"
    if ratio <= 0.85:
        return "above"
    if ratio >= 1.15:
        return "below"
    return "average"


def _metric_value(row: dict[str, Any], stat: str) -> float | int | None:
    v = row.get(stat)
    if v is None:
        return None
    return v


def _insight_card(
    stat_type: str,
    value: float | int | None,
    benchmark: float | None,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "stat": stat_type,
        "label": STAT_LABELS.get(stat_type, stat_type),
        "value": value,
        "benchmark": benchmark,
        "badge": performance_badge(value, benchmark, stat_type=stat_type),
        "insight": generate_insight_safe(stat_type, value, context),
    }


@lru_cache(maxsize=32)
def _cached_match_summary(match_id: int, payload_json: str) -> str:
    return generate_match_summary(json.loads(payload_json))


def _build_match_payload(
    match: dict[str, Any],
    teams: list[dict[str, Any]],
    players: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "match": match,
        "teams": teams,
        "top_players": players[:8],
        "player_count": len(players),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"app": "StatSense", "docs": "/docs"}


@app.get("/matches")
def get_matches() -> list[dict[str, Any]]:
    with db() as conn:
        return list_matches(conn)


@app.get("/match/{match_id}")
def get_match_detail(match_id: int) -> dict[str, Any]:
    with db() as conn:
        match = get_match(conn, match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        teams = get_team_stats_for_match(conn, match_id)
        players = get_player_stats_for_match(conn, match_id)
        match_avgs = get_match_player_averages(conn, match_id)
        team_avgs = get_team_stat_averages(conn)

        title = _match_title(match)
        payload = _build_match_payload(match, teams, players)

        try:
            summary = _cached_match_summary(match_id, json.dumps(payload, default=str))
        except Exception:
            summary = (
                f"{match['home_team']} beat {match['away_team']} "
                f"{match['home_score']}-{match['away_score']} on {match['date']}."
            )

        team_cards = []
        for t in teams:
            benchmarks = {
                stat: {
                    "value": _metric_value(t, stat),
                    "league_average": team_avgs.get(stat),
                    "badge": performance_badge(
                        _metric_value(t, stat),
                        team_avgs.get(stat),
                        stat_type=stat,
                    ),
                }
                for stat in TEAM_METRICS
                if _metric_value(t, stat) is not None
            }
            team_cards.append(
                {"team": t["team"], "stats": t, "benchmarks": benchmarks}
            )

        top_performers = []
        for p in players[:3]:
            best_stat = "xg"
            best_val = p.get("xg") or 0
            if (p.get("goals") or 0) > best_val:
                best_stat, best_val = "goals", p.get("goals")
            top_performers.append(
                {
                    "player_id": p["player_id"],
                    "player_name": p["player_name"],
                    "team": p["team"],
                    "position": p.get("position"),
                    "highlight_stat": best_stat,
                    "highlight_value": best_val,
                    "goals": p.get("goals"),
                    "assists": p.get("assists"),
                    "xg": p.get("xg"),
                    "insight": generate_insight_safe(
                        best_stat,
                        best_val,
                        {
                            "player": p["player_name"],
                            "match": title,
                            "benchmark": match_avgs.get(best_stat),
                        },
                    ),
                }
            )

        return {
            "match": match,
            "summary": summary,
            "teams": team_cards,
            "top_performers": top_performers,
            "players": players,
        }


@app.get("/match/{match_id}/player/{player_id}")
def get_player_in_match(match_id: int, player_id: int) -> dict[str, Any]:
    with db() as conn:
        match = get_match(conn, match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        player = get_player_match_row(conn, match_id, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found in this match")

        match_avgs = get_match_player_averages(conn, match_id)
        team_players = [
            p
            for p in get_player_stats_for_match(conn, match_id)
            if p["team"] == player["team"]
        ]
        team_avgs = {}
        if team_players:
            for stat in PLAYER_METRICS:
                vals = [p[stat] for p in team_players if p.get(stat) is not None]
                if vals and isinstance(vals[0], (int, float)):
                    team_avgs[stat] = round(sum(vals) / len(vals), 3)

        title = _match_title(match)
        insight_cards = []
        comparison = {}
        for stat in PLAYER_METRICS:
            val = _metric_value(player, stat)
            if val is None:
                continue
            bench = match_avgs.get(stat)
            team_bench = team_avgs.get(stat)
            insight_cards.append(
                _insight_card(
                    stat,
                    val,
                    bench,
                    {
                        "player": player["player_name"],
                        "team": player["team"],
                        "match": title,
                        "benchmark": bench,
                    },
                )
            )
            comparison[stat] = {
                "player": val,
                "match_average": bench,
                "team_average": team_bench,
            }

        return {
            "match": match,
            "player": player,
            "insight_cards": [c for c in insight_cards if c],
            "comparison": comparison,
        }


@app.get("/player/{player_id}/season")
def get_player_season(player_id: int) -> dict[str, Any]:
    with db() as conn:
        rows = get_player_season_stats(conn, player_id)
        if not rows:
            raise HTTPException(status_code=404, detail="Player not found")

        aggregated = aggregate_player_season(rows)
        player_name = rows[0]["player_name"]
        team = rows[0]["team"]

        trend = [
            {
                "match_id": r["match_id"],
                "date": r["match_date"],
                "opponent": (
                    r["away_team"]
                    if r["team"] == r["home_team"]
                    else r["home_team"]
                ),
                "goals": r.get("goals"),
                "assists": r.get("assists"),
                "xg": r.get("xg"),
                "xa": r.get("xa"),
                "competition": r.get("competition"),
            }
            for r in rows
        ]

        trend_text = generate_insight_safe(
            "xg",
            aggregated.get("avg_xg_per_match") or 0,
            {
                "player": player_name,
                "match": f"{aggregated['matches_played']} matches in dataset",
                "benchmark": round(
                    sum(t["xg"] or 0 for t in trend) / max(len(trend), 1), 3
                ),
            },
        )

        return {
            "player_id": player_id,
            "player_name": player_name,
            "team": team,
            "aggregated": aggregated,
            "matches": trend,
            "trend_analysis": trend_text,
        }


PLAYER_COMPARE_STATS = [
    "goals",
    "assists",
    "xg",
    "xa",
    "pass_accuracy_pct",
    "key_passes",
    "progressive_passes",
    "duels_won_pct",
]


@app.get("/match/{match_id}/timeline")
def get_match_timeline(match_id: int) -> dict[str, Any]:
    with db() as conn:
        match = get_match(conn, match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        events = get_match_events(conn, match_id)
        return {"match_id": match_id, "events": events}


@app.post("/match/{match_id}/compare", response_model=CompareResponse)
def compare_players_in_match(match_id: int, body: CompareRequest) -> CompareResponse:
    if body.player_a_id == body.player_b_id:
        raise HTTPException(status_code=400, detail="Choose two different players")

    with db() as conn:
        match = get_match(conn, match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        player_a = get_player_match_row(conn, match_id, body.player_a_id)
        player_b = get_player_match_row(conn, match_id, body.player_b_id)
        if not player_a or not player_b:
            raise HTTPException(status_code=404, detail="Player not found in this match")

        title = _match_title(match)
        stat_rows = []
        for stat in PLAYER_COMPARE_STATS:
            va = _metric_value(player_a, stat)
            vb = _metric_value(player_b, stat)
            if va is None and vb is None:
                continue
            winner = None
            if va is not None and vb is not None:
                if va > vb:
                    winner = "a"
                elif vb > va:
                    winner = "b"
            stat_rows.append(
                {
                    "stat": stat,
                    "label": STAT_LABELS.get(stat, stat),
                    "player_a": va,
                    "player_b": vb,
                    "leader": winner,
                }
            )

        try:
            verdict = compare_players_verdict(player_a, player_b, title)
        except Exception:
            verdict = (
                f"{player_a['player_name']} and {player_b['player_name']} both had "
                f"notable roles — compare goals ({player_a.get('goals')} vs "
                f"{player_b.get('goals')}) and xG ({player_a.get('xg')} vs {player_b.get('xg')})."
            )

        return CompareResponse(
            player_a={
                "player_id": player_a["player_id"],
                "player_name": player_a["player_name"],
                "team": player_a["team"],
            },
            player_b={
                "player_id": player_b["player_id"],
                "player_name": player_b["player_name"],
                "team": player_b["team"],
            },
            stats=stat_rows,
            verdict=verdict,
        )


@app.post("/match/{match_id}/timeline/explain")
def explain_event(match_id: int, body: ExplainEventRequest) -> dict[str, Any]:
    with db() as conn:
        match = get_match(conn, match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        event = get_match_event(conn, match_id, body.event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        teams = get_team_stats_for_match(conn, match_id)
        try:
            insight = explain_timeline_event(event, match, teams)
        except Exception:
            insight = (
                f"At {event['minute']}', {event.get('player_name') or 'a player'} "
                f"was involved in a {event.get('event_type')} ({event.get('detail')})."
            )

        return {"event": event, "insight": insight}


@app.post("/ask", response_model=AskResponse)
def ask_about_match(body: AskRequest) -> AskResponse:
    with db() as conn:
        match = get_match(conn, body.match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        teams = get_team_stats_for_match(conn, body.match_id)
        players = get_player_stats_for_match(conn, body.match_id)
        payload = _build_match_payload(match, teams, players)

        try:
            answer = answer_fan_question(body.question, payload)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"AI service unavailable: {exc}",
            ) from exc

        return AskResponse(
            question=body.question,
            answer=answer,
            match_id=body.match_id,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
