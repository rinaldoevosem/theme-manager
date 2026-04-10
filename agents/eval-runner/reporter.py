"""Generate markdown reports from eval scores."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from scorer import grade_letter


def generate_report(
    run_id: str,
    cases: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    feedback: dict[str, Any],
    previous_scores: list[dict[str, Any]] | None = None,
) -> str:
    """Generate a markdown report for an eval run."""
    cases_by_id = {c["id"]: c for c in cases}
    n = max(len(scores), 1)

    # Summary stats
    avg_composite = sum(s["composite"] for s in scores) / n
    avg_accuracy = sum(s["accuracy"] for s in scores) / n
    avg_reasoning = sum(s["reasoning"] for s in scores) / n
    avg_completeness = sum(s["completeness"] for s in scores) / n
    total_cost = sum(s.get("cost_usd", 0) for s in scores)
    avg_cost = total_cost / n
    avg_duration = sum(s.get("duration_ms", 0) for s in scores) / n / 1000  # seconds
    pass_rate = feedback["pass_rate"]

    # Grade distribution
    grades: dict[str, list[dict]] = {"A": [], "B": [], "C": [], "F": []}
    for s in scores:
        grades[grade_letter(s["composite"])].append(s)

    lines: list[str] = []
    lines.append(f"# Eval Run: {run_id}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Cases run | {len(scores)} |")
    lines.append(f"| Pass rate (accuracy ≥ 0.6) | **{pass_rate:.0%}** ({feedback['successes']}/{len(scores)}) |")
    lines.append(f"| Avg composite score | **{avg_composite:.3f}** |")
    lines.append(f"| Avg accuracy | {avg_accuracy:.3f} |")
    lines.append(f"| Avg reasoning | {avg_reasoning:.3f} |")
    lines.append(f"| Avg completeness | {avg_completeness:.3f} |")
    lines.append(f"| Total cost | ${total_cost:.2f} |")
    lines.append(f"| Avg cost/task | ${avg_cost:.3f} |")
    lines.append(f"| Avg duration/task | {avg_duration:.1f}s |")
    lines.append("")

    # Grade distribution
    lines.append("## Grade Distribution")
    lines.append("")
    lines.append("| Grade | Count | Cases |")
    lines.append("|-------|-------|-------|")
    for grade in ("A", "B", "C", "F"):
        case_ids = [s["case_id"] for s in grades[grade][:8]]
        more = f" +{len(grades[grade]) - 8} more" if len(grades[grade]) > 8 else ""
        lines.append(f"| {grade} | {len(grades[grade])} | {', '.join(case_ids)}{more} |")
    lines.append("")

    # Suite breakdown
    lines.append("## Suite Performance")
    lines.append("")
    lines.append("| Suite | Cases | Pass Rate | Avg Composite |")
    lines.append("|-------|-------|-----------|---------------|")
    for suite, stats in sorted(feedback["suite_stats"].items()):
        lines.append(
            f"| {suite} | {stats['count']} | {stats['pass_rate']:.0%} | {stats['avg_composite']:.3f} |"
        )
    lines.append("")

    # Failures
    failures = [s for s in scores if s["composite"] < 0.5]
    if failures:
        lines.append(f"## Failures ({len(failures)})")
        lines.append("")
        for s in failures[:15]:
            case = cases_by_id.get(s["case_id"], {})
            gt = case.get("ground_truth", {})
            acc_details = s.get("details", {}).get("accuracy", {})
            recommended = acc_details.get("recommended_sections", [])

            lines.append(f"### {s['case_id']} — {grade_letter(s['composite'])} ({s['composite']:.3f})")
            lines.append("")
            lines.append(f"**Title:** {case.get('title', s.get('title', '(unknown)'))}")
            lines.append("")
            lines.append(f"- **Expected:** {', '.join(gt.get('expected_sections', []))}")
            lines.append(f"- **Got:** {', '.join(recommended[:3]) if recommended else '(none)'}")
            lines.append(f"- **Verdict:** {acc_details.get('verdict', 'unknown')}")
            lines.append(
                f"- **Sub-scores:** acc={s['accuracy']:.2f} reason={s['reasoning']:.2f} "
                f"complete={s['completeness']:.2f} cost={s['cost']:.2f} speed={s['speed']:.2f}"
            )
            lines.append("")
        if len(failures) > 15:
            lines.append(f"_...and {len(failures) - 15} more failures._")
            lines.append("")

    # Suggestions
    if feedback.get("suggestions"):
        lines.append("## Improvement Suggestions")
        lines.append("")
        for i, s in enumerate(feedback["suggestions"], 1):
            lines.append(f"{i}. {s}")
        lines.append("")

    # Section confusion
    if feedback.get("section_confusion"):
        lines.append("## Section Confusion Pairs")
        lines.append("")
        lines.append("| Expected → Got | Count |")
        lines.append("|----------------|-------|")
        for pair, count in feedback["section_confusion"].items():
            lines.append(f"| {pair} | {count} |")
        lines.append("")

    # Trend comparison
    if previous_scores:
        prev_n = max(len(previous_scores), 1)
        prev_avg_composite = sum(s["composite"] for s in previous_scores) / prev_n
        prev_pass = sum(1 for s in previous_scores if s["accuracy"] >= 0.6) / prev_n
        prev_avg_cost = sum(s.get("cost_usd", 0) for s in previous_scores) / prev_n

        lines.append("## Trend (vs previous run)")
        lines.append("")
        lines.append("| Metric | Previous | Current | Δ |")
        lines.append("|--------|----------|---------|---|")
        lines.append(
            f"| Pass rate | {prev_pass:.0%} | {pass_rate:.0%} | "
            f"{(pass_rate - prev_pass) * 100:+.1f}% |"
        )
        lines.append(
            f"| Avg composite | {prev_avg_composite:.3f} | {avg_composite:.3f} | "
            f"{avg_composite - prev_avg_composite:+.3f} |"
        )
        lines.append(
            f"| Avg cost | ${prev_avg_cost:.3f} | ${avg_cost:.3f} | "
            f"${avg_cost - prev_avg_cost:+.3f} |"
        )
        lines.append("")

    return "\n".join(lines)


def print_terminal_summary(scores: list[dict], feedback: dict, report_path: Path) -> None:
    """Print a 5-line summary to stdout."""
    n = max(len(scores), 1)
    avg_composite = sum(s["composite"] for s in scores) / n
    total_cost = sum(s.get("cost_usd", 0) for s in scores)

    print()
    print("=" * 70)
    print(f"  Eval Complete  |  Pass Rate: {feedback['pass_rate']:.0%}  |  Avg Score: {avg_composite:.3f}")
    print(f"  Cases: {len(scores)}  |  Failures: {feedback['failures']}  |  Total Cost: ${total_cost:.2f}")
    if feedback.get("suggestions"):
        print(f"  Top Suggestion: {feedback['suggestions'][0][:100]}")
    print(f"  Report: {report_path}")
    print("=" * 70)


def find_previous_run(results_dir: Path, current_run_id: str) -> Path | None:
    """Find the most recent previous run directory."""
    if not results_dir.exists():
        return None
    runs = sorted(
        [p for p in results_dir.glob("run_*") if p.is_dir() and p.name != f"run_{current_run_id}"]
    )
    return runs[-1] if runs else None


def load_previous_scores(results_dir: Path, current_run_id: str) -> list[dict] | None:
    """Load scores.json from the most recent previous run."""
    prev = find_previous_run(results_dir, current_run_id)
    if not prev:
        return None
    scores_file = prev / "scores.json"
    if not scores_file.exists():
        return None
    return json.loads(scores_file.read_text())
