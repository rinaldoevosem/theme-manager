# Eval Runner — Agent Instructions

## Overview

Plain Python eval system that grades the **theme-architect** agent on a battery of test cases. Creates Paperclip tasks, triggers the architect's heartbeat, scores results, and generates a report.

**Not an LLM agent** — this is deterministic Python with $0 runtime cost (the only LLM spend is on the theme-architect runs being evaluated).

## Quick Start

```bash
cd /Users/melo/shopify-theme/agents/eval-runner
.venv/bin/python3.14 main.py --overnight
```

This runs the full loop: load cases → create Paperclip tasks → trigger architect heartbeat → poll for completion → score → generate report.

Expect ~2 hours runtime for 40 cases at ~$6-8 in LLM costs.

## Commands

| Command | Purpose |
|---------|---------|
| `python main.py --overnight` | Full eval loop end-to-end |
| `python main.py --create-tasks` | Just create Paperclip tasks (no run) |
| `python main.py --score <run_dir>` | Re-score a previous run from raw_results.json |
| `python main.py --report <run_dir>` | Regenerate report from existing scores |
| `python main.py --list-runs` | Show summary of all previous eval runs |

## Output

Each run writes to `results/run_YYYY-MM-DDTHH:MM/`:

- `task_map.json` — case_id ↔ Paperclip issue_id mapping
- `raw_results.json` — agent output, costs, durations from Paperclip
- `scores.json` — per-case scores across 5 dimensions
- `feedback.json` — failure patterns and improvement suggestions
- `report.md` — human-readable summary (read this in the morning)

## Scoring Dimensions

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| Accuracy | 40% | Did the top recommendation match ground truth? |
| Reasoning | 25% | Did the agent cite specific blocks/settings/schema? |
| Completeness | 15% | Did it mention alternatives and gaps? |
| Cost | 10% | $0.15/task target |
| Speed | 10% | 60s/task target |

## Test Case Files

`eval_cases/*.yaml` — ~40 cases across 9 categories. To add cases, create or edit a YAML file following the existing format.

## See Also

- `tasks.md` — future work tracker
- `../theme-architect/` — the agent being evaluated
