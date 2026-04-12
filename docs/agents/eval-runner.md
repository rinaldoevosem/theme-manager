---
title: Eval Runner
tags: [agent, eval-runner]
created: 2026-04-11
updated: 2026-04-11
---

# Eval Runner

> [!info] Deterministic Python evaluation harness that tests the [[agents/theme-architect|Theme Architect]] against a battery of test cases. Not an LLM agent — no Claude API cost for the runner itself.

## Overview

| Property | Value |
|----------|-------|
| **Type** | Plain Python (not an LLM agent) |
| **Evaluates** | Theme Architect |
| **Test Cases** | 40 cases across 9 YAML suites |
| **Scoring** | 5 dimensions, weighted composite score |
| **Runtime Cost** | $0 (LLM cost is charged to the architect) |
| **Directory** | `agents/eval-runner/` |

## How It Works

```
1. Load eval cases from YAML files
2. Create synthetic Paperclip tasks assigned to the architect
3. Trigger the architect's heartbeat (subprocess)
4. Capture stdout → extract cost/duration per task
5. Score each response across 5 dimensions
6. Generate a markdown report with pass/fail and improvement suggestions
```

## Scoring Dimensions

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| **Accuracy** | 40% | Correct section recommendations |
| **Reasoning** | 25% | Quality of explanation and justification |
| **Completeness** | 15% | All design requirements addressed |
| **Cost** | 10% | Token/dollar efficiency |
| **Speed** | 10% | Response time |

## CLI Usage

```bash
# Full eval loop (load → create tasks → run → score → report)
python main.py --overnight

# Create Paperclip tasks only (no run)
python main.py --create-tasks

# Re-score a previous run from raw results
python main.py --score results/run_2026-04-09T10:30/

# Regenerate report from existing scores
python main.py --report results/run_2026-04-09T10:30/

# List all previous runs
python main.py --list-runs

# Filter by suite
python main.py --overnight --suite hero-sections

# Limit cases
python main.py --overnight --max-cases 10

# Create tasks without running heartbeat
python main.py --overnight --skip-run

# Clean up leftover eval tasks from Paperclip
python main.py --cleanup-eval-tasks
```

> [!warning] Runtime
> A full `--overnight` run with 40 cases takes approximately 2 hours and costs $6-8 (charged to the architect agent's budget).

## Baseline Results (2026-04-09)

| Metric | Result |
|--------|--------|
| Pass rate | 90% (9/10 cases in initial subset) |
| Avg composite score | ~0.72 |
| Avg cost per case | $0.35-0.40 |
| Known issues | Cost target too tight ($0.15 vs realistic $0.40), collection-editorial confusion |

## Test Case Structure

Each YAML file defines a suite of test cases:

```yaml
- id: hero-banner-basic
  suite: hero-sections
  title: "Match a basic hero banner design"
  description: "Full-width hero with image, heading, subtext, CTA button"
  expected_sections: ["hero-banner"]
  expected_blocks: ["heading", "subtext", "button"]
  difficulty: easy
```

### Suites

| Suite | Cases | Focus |
|-------|-------|-------|
| `hero-sections` | ~5 | Hero banners, slideshows |
| `product-sections` | ~5 | Product grids, featured products |
| `collection-sections` | ~5 | Collection lists, filters |
| `content-sections` | ~5 | Rich text, image galleries |
| `navigation-sections` | ~4 | Headers, footers, menus |
| `promotional-sections` | ~4 | Banners, announcements |
| `social-sections` | ~3 | Testimonials, reviews |
| `utility-sections` | ~4 | Newsletters, contact forms |
| `composite-sections` | ~5 | Multi-section page layouts |

## Output Structure

Each run produces a directory:

```
results/run_YYYY-MM-DDTHH:MM/
  raw_results.json      # Raw architect responses per case
  scores.json           # Computed scores per case
  report.md             # Human-readable markdown report
  feedback.json         # Improvement suggestions by failure pattern
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — orchestrates the full eval lifecycle |
| `config.py` | Configuration — paths, timeouts, Paperclip API details |
| `eval_cases.py` | Load and filter YAML eval cases |
| `scorer.py` | 5-dimension scoring logic |
| `feedback.py` | Analyze failure patterns, suggest improvements |
| `reporter.py` | Generate human-readable markdown reports |
| `paperclip_client.py` | Async HTTP client for Paperclip API |
| `eval_cases/` | 9 YAML suite files with 40 test cases |
| `results/` | Output from previous runs |

## Configuration

Key environment variables (in `.env`):

| Variable | Required | Description |
|----------|----------|-------------|
| `PAPERCLIP_API_URL` | Yes | Default: `http://localhost:3100` |
| `PAPERCLIP_COMPANY_ID` | Yes | Company ID for task creation |
| `ARCHITECT_AGENT_ID` | Yes | Agent ID of the theme-architect |
| `ARCHITECT_DIR` | Yes | Path to `agents/theme-architect/` |
| `THEME_DIR` | Yes | Path to theme repo for context |
| `MAX_CASES` | No | Default: 40 |
| `TIMEOUT_PER_CASE_MIN` | No | Default: 3 minutes |
