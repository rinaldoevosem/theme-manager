"""Score eval results across 5 dimensions."""

from __future__ import annotations

import re
from typing import Any

# Weights for composite score
WEIGHTS = {
    "accuracy": 0.40,
    "reasoning": 0.25,
    "completeness": 0.15,
    "cost": 0.10,
    "speed": 0.10,
}

TARGET_COST_USD = 0.15
TARGET_DURATION_MS = 60_000

_SECTION_RE = re.compile(r"sections?[/\\]([\w-]+\.liquid)", re.IGNORECASE)
_BARE_SECTION_RE = re.compile(r"`([\w-]+\.liquid)`")


def extract_recommended_sections(output: str) -> list[str]:
    """Extract section filenames mentioned in agent output, in order of appearance.

    Looks for patterns like `sections/hero.liquid`, `hero.liquid`, etc.
    Returns deduplicated list preserving first-mention order.
    """
    matches: list[str] = []
    seen: set[str] = set()

    # First pass: with sections/ prefix (more confident matches)
    for m in _SECTION_RE.finditer(output):
        name = m.group(1).lower()
        if name not in seen:
            seen.add(name)
            matches.append(name)

    # Second pass: bare backtick-quoted .liquid filenames
    for m in _BARE_SECTION_RE.finditer(output):
        name = m.group(1).lower()
        if name not in seen:
            seen.add(name)
            matches.append(name)

    return matches


def score_accuracy(output: str, ground_truth: dict[str, Any]) -> tuple[float, dict]:
    """Did the agent recommend the right section?

    Returns (score, details).
    """
    recommended = extract_recommended_sections(output)
    expected = {s.lower() for s in ground_truth.get("expected_sections", [])}
    acceptable = {s.lower() for s in ground_truth.get("acceptable_sections", [])}

    details = {
        "recommended_sections": recommended[:5],
        "expected": sorted(expected),
        "acceptable": sorted(acceptable),
    }

    if not recommended:
        return 0.0, {**details, "verdict": "no_section_recommended"}

    top = recommended[0]
    if top in expected:
        return 1.0, {**details, "verdict": "top_match_expected"}
    if top in acceptable:
        return 0.6, {**details, "verdict": "top_match_acceptable"}

    # Check if expected appears anywhere in recommendations (partial credit)
    if expected & set(recommended):
        return 0.5, {**details, "verdict": "expected_mentioned_not_top"}
    if acceptable & set(recommended):
        return 0.3, {**details, "verdict": "acceptable_mentioned_not_top"}

    return 0.0, {**details, "verdict": "wrong_section"}


def score_reasoning(output: str, case: dict[str, Any]) -> tuple[float, dict]:
    """Did the agent cite specific blocks, settings, schema?"""
    output_lower = output.lower()
    scoring = case.get("scoring", {})

    must_mention = scoring.get("must_mention", []) or []
    found_mentions = []
    missing_mentions = []

    for term in must_mention:
        if term.lower() in output_lower:
            found_mentions.append(term)
        else:
            missing_mentions.append(term)

    # Bonus checks
    has_schema_quotes = bool(re.search(r'"type"\s*:\s*"', output))
    has_file_paths = bool(re.search(r"sections/[\w-]+\.liquid", output))
    has_block_mentions = "block" in output_lower
    has_setting_mentions = "setting" in output_lower

    bonus_score = sum([has_schema_quotes, has_file_paths, has_block_mentions, has_setting_mentions])

    if must_mention:
        mention_score = len(found_mentions) / len(must_mention)
    else:
        mention_score = 0.5  # Neutral if no required terms

    # Weighted: 60% required mentions, 40% bonus
    total = mention_score * 0.6 + (bonus_score / 4) * 0.4

    return min(1.0, total), {
        "found_mentions": found_mentions,
        "missing_mentions": missing_mentions,
        "has_schema_quotes": has_schema_quotes,
        "has_file_paths": has_file_paths,
    }


def score_completeness(output: str, case: dict[str, Any]) -> tuple[float, dict]:
    """Did the agent address alternatives, gaps, configuration?"""
    output_lower = output.lower()
    scoring = case.get("scoring", {})

    score = 0.0
    details = {}

    # Mentions alternatives?
    alt_words = ["alternative", "also consider", "runner-up", "second choice", "alternatively", "or use"]
    has_alternatives = any(w in output_lower for w in alt_words)
    if has_alternatives:
        score += 0.35
    details["has_alternatives"] = has_alternatives

    # Flags gaps when expected
    must_flag_gaps = scoring.get("must_flag_gaps", False)
    gap_words = ["gap", "limitation", "cannot", "missing", "would need", "doesn't support", "no support"]
    has_gap_mention = any(w in output_lower for w in gap_words)
    details["has_gap_mention"] = has_gap_mention

    if must_flag_gaps:
        if has_gap_mention:
            score += 0.35
        # Penalty for missing required gap mention
    else:
        score += 0.25  # Neutral credit when not required

    # Mentions configuration/customization
    config_words = ["adjust", "configure", "set the", "change the", "enable", "preset", "settings:"]
    has_config = any(w in output_lower for w in config_words)
    if has_config:
        score += 0.30
    details["has_config_mention"] = has_config

    return min(1.0, score), details


def score_cost(cost_usd: float) -> tuple[float, dict]:
    if cost_usd <= 0:
        return 0.5, {"cost_usd": cost_usd, "verdict": "no_data"}
    if cost_usd <= TARGET_COST_USD:
        return 1.0, {"cost_usd": cost_usd, "verdict": "within_target"}
    if cost_usd <= TARGET_COST_USD * 2:
        return 0.5, {"cost_usd": cost_usd, "verdict": "above_target"}
    return 0.0, {"cost_usd": cost_usd, "verdict": "expensive"}


def score_speed(duration_ms: int) -> tuple[float, dict]:
    if duration_ms <= 0:
        return 0.5, {"duration_ms": duration_ms, "verdict": "no_data"}
    if duration_ms <= TARGET_DURATION_MS:
        return 1.0, {"duration_ms": duration_ms, "verdict": "fast"}
    if duration_ms <= TARGET_DURATION_MS * 2:
        return 0.5, {"duration_ms": duration_ms, "verdict": "slow"}
    return 0.0, {"duration_ms": duration_ms, "verdict": "very_slow"}


def score_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Score a single eval case against its raw result.

    `result` should have: output (str), cost_usd (float), duration_ms (int), status (str).
    """
    output = result.get("output", "") or ""
    status = result.get("status", "unknown")

    # If the task failed entirely, all scores are 0
    if status not in ("done", "completed") or not output:
        return {
            "case_id": case["id"],
            "suite": case.get("suite", "unknown"),
            "status": status,
            "composite": 0.0,
            "accuracy": 0.0,
            "reasoning": 0.0,
            "completeness": 0.0,
            "cost": 0.0,
            "speed": 0.0,
            "details": {"error": "task did not complete or empty output"},
        }

    accuracy, acc_details = score_accuracy(output, case["ground_truth"])
    reasoning, reason_details = score_reasoning(output, case)
    completeness, comp_details = score_completeness(output, case)
    cost, cost_details = score_cost(result.get("cost_usd", 0.0))
    speed, speed_details = score_speed(result.get("duration_ms", 0))

    composite = (
        accuracy * WEIGHTS["accuracy"]
        + reasoning * WEIGHTS["reasoning"]
        + completeness * WEIGHTS["completeness"]
        + cost * WEIGHTS["cost"]
        + speed * WEIGHTS["speed"]
    )

    return {
        "case_id": case["id"],
        "suite": case.get("suite", "unknown"),
        "title": case.get("title", ""),
        "status": status,
        "composite": round(composite, 3),
        "accuracy": round(accuracy, 3),
        "reasoning": round(reasoning, 3),
        "completeness": round(completeness, 3),
        "cost": round(cost, 3),
        "speed": round(speed, 3),
        "cost_usd": result.get("cost_usd", 0.0),
        "duration_ms": result.get("duration_ms", 0),
        "details": {
            "accuracy": acc_details,
            "reasoning": reason_details,
            "completeness": comp_details,
            "cost": cost_details,
            "speed": speed_details,
        },
    }


def score_all(cases: list[dict[str, Any]], results_by_case: dict[str, dict]) -> list[dict]:
    """Score all cases. results_by_case maps case_id -> raw result dict."""
    return [score_case(c, results_by_case.get(c["id"], {})) for c in cases]


def grade_letter(composite: float) -> str:
    if composite >= 0.9:
        return "A"
    if composite >= 0.7:
        return "B"
    if composite >= 0.5:
        return "C"
    return "F"
