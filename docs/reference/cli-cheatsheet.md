---
title: CLI Cheatsheet
tags: [reference]
created: 2026-04-11
updated: 2026-04-11
---

# CLI Cheatsheet

All agents run from their respective directories under `agents/`. Activate the venv first:

```bash
cd agents/<agent-name>
source .venv/bin/activate
```

## Theme Manager

```bash
# Run with a prompt
python main.py "Give me a full status report of all three environments"

# Launch browser-based setup wizard
python main.py --setup

# Setup for a specific store
python main.py --setup --store-domain horizon-clone.myshopify.com

# Heartbeat mode (automated health check, runs every 4h via cron)
python main.py --heartbeat
```

### Paperclip Commands

```bash
# Status report
python main.py "Give me a full status report of all three theme environments"

# Sync drift detection
python main.py "Use the sync-checker to detect any drift between GitHub repos and Shopify themes"

# PR review
python main.py "Use the pr-reviewer to review all open PRs across the three theme repos"

# Client-facing report
python main.py "Use the stakeholder-reporter to generate a client-facing status report"

# Technical team report
python main.py "Use the stakeholder-reporter to generate a technical team status report"

# Start promotion
python main.py "Check promotion readiness for the dev environment and guide me through promoting to staging"
```

## Theme Architect

```bash
# Run with a prompt
python main.py "Analyze the full theme architecture"

# Heartbeat mode (runs every 6h via cron)
python main.py --heartbeat

# Override model (e.g. Opus for complex analysis)
python main.py --model claude-opus-4-6 "Match this design to existing sections"
```

### Paperclip Commands

```bash
# Full architecture overview
python main.py "Analyze the full theme architecture and provide a summary of all sections"

# Match Figma design to sections
python main.py "Match this Figma design to the best existing section: <figma_url>"

# Section deep-dive
python main.py "Give me a detailed analysis of the hero-banner section"

# Extract design requirements
python main.py "Extract the structural requirements from this design: <description>"
```

## Theme Designer

```bash
# Apply design from Figma
python main.py "Apply the design tokens from this Figma file: <figma_url>"

# Dry run (preview without writing)
python main.py --dry-run "Apply design tokens from <figma_url>"

# Heartbeat mode (runs every 6h via cron)
python main.py --heartbeat

# Override model
python main.py --model claude-opus-4-6 "Apply design tokens from <figma_url>"
```

### Paperclip Commands

```bash
# Apply design tokens
python main.py "Apply the design tokens from this Figma file to the theme settings: <figma_url>"

# Preview changes
python main.py --dry-run "Preview what changes would be made from this Figma design: <figma_url>"

# Parse all settings
python main.py "Parse and summarize all configurable theme settings from settings_schema.json"
```

## Eval Runner

```bash
# Full evaluation loop (~2h, $6-8)
python main.py --overnight

# Create Paperclip tasks only (no run)
python main.py --create-tasks

# Re-score a previous run
python main.py --score results/run_2026-04-09T10:30/

# Regenerate report
python main.py --report results/run_2026-04-09T10:30/

# List all previous runs
python main.py --list-runs

# Filter by suite
python main.py --overnight --suite hero-sections

# Limit number of cases
python main.py --overnight --max-cases 10

# Create tasks but skip running the heartbeat
python main.py --overnight --skip-run

# Clean up leftover eval tasks
python main.py --cleanup-eval-tasks
```

## Utility Commands

```bash
# Refresh Google Fonts dataset (quarterly)
cd agents/theme-designer
python scripts/fetch_google_fonts.py

# Check git status of the agent repo
git status

# Check theme repo status
cd horizon-clone/repo-main && git status
```
