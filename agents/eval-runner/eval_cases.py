"""Loader for eval case YAML files."""

from pathlib import Path
from typing import Any

import yaml


def load_eval_cases(cases_dir: Path, suite_filter: str | None = None) -> list[dict[str, Any]]:
    """Load all eval cases from YAML files in cases_dir.

    Each YAML file contains:
        suite: "Suite Name"
        cases:
          - id: "..."
            title: "..."
            description: "..."
            ground_truth: { expected_sections: [...], acceptable_sections: [...] }
            scoring: { must_mention: [...], must_flag_gaps: bool }

    Returns a flat list of cases with `suite` field added to each.
    """
    cases: list[dict[str, Any]] = []

    for yaml_file in sorted(cases_dir.glob("*.yaml")):
        with yaml_file.open("r") as f:
            data = yaml.safe_load(f)

        if not data or "cases" not in data:
            continue

        suite = data.get("suite", yaml_file.stem)
        if suite_filter and suite_filter.lower() not in suite.lower():
            continue

        for case in data["cases"]:
            case["suite"] = suite
            case["source_file"] = yaml_file.name
            cases.append(case)

    return cases


def validate_case(case: dict[str, Any]) -> list[str]:
    """Validate a single eval case. Returns list of error messages (empty if valid)."""
    errors = []
    required = ["id", "title", "description", "ground_truth"]
    for key in required:
        if key not in case:
            errors.append(f"Missing required field: {key}")

    if "ground_truth" in case:
        gt = case["ground_truth"]
        if not isinstance(gt, dict):
            errors.append("ground_truth must be a dict")
        elif "expected_sections" not in gt:
            errors.append("ground_truth.expected_sections is required")
        elif not isinstance(gt["expected_sections"], list):
            errors.append("ground_truth.expected_sections must be a list")

    return errors
