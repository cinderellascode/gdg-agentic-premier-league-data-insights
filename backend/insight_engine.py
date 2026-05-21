"""
AI insight generation for StatSense using the Groq API.

Set GROQ_API_KEY in your environment (or .env). Optional: GROQ_MODEL.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_MODEL = "llama-3.3-70b-versatile"

STAT_LABELS: dict[str, str] = {
    "goals": "Goals scored",
    "assists": "Assists",
    "xg": "Expected Goals (xG) — quality of scoring chances",
    "xa": "Expected Assists (xA) — quality of chances created for teammates",
    "pass_accuracy_pct": "Pass accuracy",
    "key_passes": "Key passes — passes that set up a shot",
    "progressive_passes": "Progressive passes — passes that move the ball significantly toward goal",
    "duels_won_pct": "Duels won percentage",
    "shot_accuracy_pct": "Shot accuracy — shots on target",
    "conversion_rate_pct": "Conversion rate — goals per shot",
    "possession_pct": "Possession — share of time with the ball",
    "shots_on_target": "Shots on target",
    "ppda": "PPDA — passes allowed per defensive action (lower = more intense press)",
    "xg_for": "Expected goals for the team",
    "xg_against": "Expected goals conceded",
    "pressing_intensity": "Pressing intensity — pressures per minute",
}


def _get_client():
    try:
        from groq import Groq
    except ImportError as exc:
        raise ImportError("Install groq: pip install groq") from exc

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Export your Groq API key before calling generate_insight."
        )
    return Groq(api_key=api_key)


def _build_prompt(stat_type: str, value: float | int, context: dict[str, Any]) -> str:
    label = STAT_LABELS.get(stat_type, stat_type.replace("_", " "))
    player = context.get("player")
    team = context.get("team")
    match = context.get("match")
    benchmark = context.get("benchmark") or context.get("match_avg") or context.get("league_avg")
    unit = context.get("unit", "")

    subject_parts = []
    if player:
        subject_parts.append(f"Player: {player}")
    if team:
        subject_parts.append(f"Team: {team}")
    if match:
        subject_parts.append(f"Match: {match}")
    subject = "\n".join(subject_parts) if subject_parts else "General match context"

    benchmark_line = ""
    if benchmark is not None:
        benchmark_line = f"\nBenchmark for comparison: {benchmark}{unit}"

    return f"""You are StatSense, a sports analytics assistant for everyday football fans.

Write ONE fan-friendly insight (maximum 2 sentences) about this statistic.

Rules:
- First explain what the stat means in plain English, then interpret this player's/team's value.
- Use relatable comparisons (percentages, multiples, "about X times the average").
- Tone: enthusiastic but informative, like a smart friend explaining the match.
- Never use jargon without briefly explaining it.
- Do not invent numbers — only use the values provided below.
- No bullet points, no hashtags, no emojis.

{subject}
Statistic: {label} ({stat_type})
Value: {value}{unit}{benchmark_line}

Respond with only the insight text."""


def generate_insight(
    stat_type: str,
    value: float | int,
    context: dict[str, Any] | None = None,
    *,
    model: str | None = None,
) -> str:
    """
    Generate a 1–2 sentence plain-English insight for a single statistic.

    Parameters
    ----------
    stat_type : str
        Metric key, e.g. "xg", "ppda", "pass_accuracy_pct".
    value : float | int
        The observed value for this stat.
    context : dict
        Optional keys: player, team, match, benchmark / match_avg / league_avg, unit.

    Returns
    -------
    str
        Fan-friendly insight sentence(s).

    Environment
    -----------
    GROQ_API_KEY : required
    GROQ_MODEL   : optional, defaults to llama-3.3-70b-versatile
    """
    context = context or {}
    client = _get_client()
    model = model or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    prompt = _build_prompt(stat_type, value, context)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short, accurate football insights for casual fans. "
                    "Maximum 2 sentences per response."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=120,
    )

    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Groq returned an empty insight response")
    return text


def generate_insight_fallback(
    stat_type: str,
    value: float | int,
    context: dict[str, Any] | None = None,
) -> str:
    """Offline template when GROQ_API_KEY is unavailable (dev/demo)."""
    context = context or {}
    label = STAT_LABELS.get(stat_type, stat_type)
    benchmark = context.get("benchmark") or context.get("match_avg") or context.get("league_avg")
    who = context.get("player") or context.get("team") or "They"
    if benchmark is not None and benchmark != 0:
        ratio = float(value) / float(benchmark)
        comp = f"about {ratio:.1f}× the typical {benchmark} benchmark"
    else:
        comp = f"a recorded value of {value}"
    return (
        f"{label} measures how much a player or team contributes in that area — "
        f"{who} posted {value} here, which is {comp}."
    )


def _chat(system: str, user: str, *, max_tokens: int = 400) -> str:
    client = _get_client()
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Groq returned an empty response")
    return text


def generate_match_summary(match_payload: dict[str, Any]) -> str:
    """3–4 sentence narrative of a match for the dashboard."""
    return _chat(
        "You write engaging football match summaries for casual fans. "
        "Use only the data provided. Max 4 sentences. No bullet points or emojis.",
        f"Summarize this match in plain English for fans:\n\n{json.dumps(match_payload, default=str)}",
        max_tokens=220,
    )


def compare_players_verdict(
    player_a: dict[str, Any],
    player_b: dict[str, Any],
    match_title: str,
) -> str:
    """Side-by-side AI verdict for two players in the same match."""
    return _chat(
        "You compare two football players from the same match for casual fans. "
        "Use ONLY the stats provided. One short paragraph (max 3 sentences). "
        "Name who was stronger in which areas. No bullet points or emojis.",
        f"Match: {match_title}\n\n"
        f"Player A — {player_a.get('player_name')} ({player_a.get('team')}):\n"
        f"{json.dumps({k: player_a.get(k) for k in ('goals', 'assists', 'xg', 'xa', 'pass_accuracy_pct', 'key_passes', 'progressive_passes', 'duels_won_pct') if player_a.get(k) is not None}, default=str)}\n\n"
        f"Player B — {player_b.get('player_name')} ({player_b.get('team')}):\n"
        f"{json.dumps({k: player_b.get(k) for k in ('goals', 'assists', 'xg', 'xa', 'pass_accuracy_pct', 'key_passes', 'progressive_passes', 'duels_won_pct') if player_b.get(k) is not None}, default=str)}",
        max_tokens=200,
    )


def explain_timeline_event(
    event: dict[str, Any],
    match: dict[str, Any],
    teams: list[dict[str, Any]],
) -> str:
    """Explain how a timeline moment affected the match statistically."""
    return _chat(
        "You explain a single in-match moment for football fans. "
        "Connect it to momentum or tactics using ONLY the context given. "
        "Max 2 sentences. No emojis.",
        f"Match: {match.get('home_team')} vs {match.get('away_team')} "
        f"({match.get('home_score')}-{match.get('away_score')})\n"
        f"Team stats snapshot:\n{json.dumps(teams, default=str)}\n\n"
        f"Event at {event.get('minute')}':\n{json.dumps(event, default=str)}",
        max_tokens=150,
    )


def answer_fan_question(question: str, match_payload: dict[str, Any]) -> str:
    """Answer a natural-language question about match data."""
    return _chat(
        "You are StatSense, a friendly football analyst. Answer using ONLY the stats "
        "provided. Plain English, max 4 sentences. If data is missing, say so honestly.",
        f"Match data:\n{json.dumps(match_payload, default=str)}\n\nFan question: {question}",
        max_tokens=220,
    )


def generate_insight_safe(
    stat_type: str,
    value: float | int,
    context: dict[str, Any] | None = None,
    *,
    use_fallback: bool = True,
) -> str:
    """Call Groq when configured; otherwise optional local fallback."""
    try:
        return generate_insight(stat_type, value, context)
    except (ValueError, ImportError) as exc:
        if use_fallback:
            return generate_insight_fallback(stat_type, value, context)
        raise exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test StatSense Groq insights")
    parser.add_argument("--demo", action="store_true", help="Run Messi xG example from spec")
    parser.add_argument("--fallback", action="store_true", help="Use offline template only")
    args = parser.parse_args()

    examples = [
        {
            "stat_type": "xg",
            "value": 0.87,
            "context": {
                "player": "Messi",
                "match": "Barcelona vs Eibar",
                "benchmark": 0.35,
            },
        },
        {
            "stat_type": "ppda",
            "value": 6.2,
            "context": {
                "team": "Arsenal",
                "match": "Example fixture",
                "league_avg": 11.4,
            },
        },
    ]

    for ex in examples:
        print(f"\n--- {ex['stat_type']} = {ex['value']} ---")
        if args.fallback:
            print(generate_insight_fallback(ex["stat_type"], ex["value"], ex["context"]))
        else:
            print(generate_insight(ex["stat_type"], ex["value"], ex["context"]))
