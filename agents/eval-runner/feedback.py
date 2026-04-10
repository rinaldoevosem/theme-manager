"""Failure pattern analysis and improvement suggestions."""

from __future__ import annotations

from collections import Counter
from typing import Any


def analyze(scores: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze scored results to find patterns and generate suggestions."""
    cases_by_id = {c["id"]: c for c in cases}

    failures = [s for s in scores if s["accuracy"] < 0.6]
    successes = [s for s in scores if s["accuracy"] >= 0.6]

    confusion: Counter[str] = Counter()
    missed_sections: Counter[str] = Counter()
    weak_reasoning: list[dict] = []
    cost_outliers: list[dict] = []
    suite_stats: dict[str, dict] = {}

    for score in scores:
        case = cases_by_id.get(score["case_id"], {})
        suite = score.get("suite", "unknown")
        suite_stats.setdefault(suite, {"count": 0, "sum_composite": 0.0, "sum_accuracy": 0.0, "failures": 0})
        suite_stats[suite]["count"] += 1
        suite_stats[suite]["sum_composite"] += score["composite"]
        suite_stats[suite]["sum_accuracy"] += score["accuracy"]
        if score["accuracy"] < 0.6:
            suite_stats[suite]["failures"] += 1

        # Reasoning weakness
        if score["reasoning"] < 0.5 and score["status"] in ("done", "completed"):
            weak_reasoning.append({
                "case_id": score["case_id"],
                "reasoning_score": score["reasoning"],
                "missing_mentions": score.get("details", {}).get("reasoning", {}).get("missing_mentions", []),
            })

        # Cost outliers (> 2x target)
        if score.get("cost_usd", 0) > 0.30:
            cost_outliers.append({
                "case_id": score["case_id"],
                "cost_usd": score["cost_usd"],
            })

    for fail in failures:
        case = cases_by_id.get(fail["case_id"], {})
        gt = case.get("ground_truth", {})
        expected = [s.lower() for s in gt.get("expected_sections", [])]
        recommended = (
            fail.get("details", {}).get("accuracy", {}).get("recommended_sections", [])
        )

        for exp in expected:
            if exp not in recommended:
                missed_sections[exp] += 1

            for rec in recommended[:2]:
                if rec != exp and rec not in expected:
                    confusion[f"{exp} -> {rec}"] += 1

    # Compute suite averages
    for suite, stats in suite_stats.items():
        n = max(stats["count"], 1)
        stats["avg_composite"] = round(stats["sum_composite"] / n, 3)
        stats["avg_accuracy"] = round(stats["sum_accuracy"] / n, 3)
        stats["pass_rate"] = round(1 - (stats["failures"] / n), 3)
        del stats["sum_composite"]
        del stats["sum_accuracy"]

    suggestions = _generate_suggestions(missed_sections, confusion, weak_reasoning, suite_stats)

    return {
        "total_cases": len(scores),
        "failures": len(failures),
        "successes": len(successes),
        "pass_rate": round(len(successes) / max(len(scores), 1), 3),
        "section_confusion": dict(confusion.most_common(10)),
        "missed_sections": dict(missed_sections.most_common(10)),
        "weak_reasoning_cases": weak_reasoning[:10],
        "cost_outliers": cost_outliers[:10],
        "suite_stats": suite_stats,
        "suggestions": suggestions,
    }


def _generate_suggestions(
    missed: Counter,
    confusion: Counter,
    weak_reasoning: list[dict],
    suite_stats: dict,
) -> list[str]:
    suggestions: list[str] = []

    for section, count in missed.most_common(5):
        if count >= 2:
            suggestions.append(
                f"Agent consistently fails to recommend `{section}` ({count} cases). "
                f"Consider adding hints in system_prompt.py describing when this section "
                f"is the right fit, or adjust scoring weights in tools.py."
            )

    for pair, count in confusion.most_common(5):
        if count >= 2:
            expected, got = pair.split(" -> ")
            suggestions.append(
                f"Agent confuses `{expected}` with `{got}` ({count} times). "
                f"These sections may have overlapping block types. Add differentiating "
                f"keywords in system_prompt.py or strengthen layout-match weight."
            )

    if len(weak_reasoning) >= 3:
        suggestions.append(
            f"{len(weak_reasoning)} cases had weak reasoning scores. The agent may not be "
            f"citing schema JSON or specific block/setting names. Consider adding a "
            f'"Cite specific schema fields" requirement to the system prompt.'
        )

    # Suite-level patterns
    for suite, stats in suite_stats.items():
        if stats["pass_rate"] < 0.5 and stats["count"] >= 3:
            suggestions.append(
                f"Suite '{suite}' has a low pass rate ({stats['pass_rate']:.0%}). "
                f"Consider adding domain-specific guidance for this category in the system prompt."
            )

    return suggestions
