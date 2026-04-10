# Shopify Theme Architect — Agent Instructions

## Overview

This agent is a **read-only** Shopify theme architecture expert. It analyzes theme code and Figma designs to recommend which existing section(s) best fit a given design. It **never modifies theme files**.

## First Priority: Credential Check

Before doing ANY work, verify that per-store credentials exist. This agent reuses the `.env` files created by the **theme-manager** setup wizard.

```bash
# Check if the store's .env exists
cat /Users/melo/shopify-theme/{store-slug}/.env
```

If credentials are missing, **do not launch a setup wizard** — this agent doesn't have one. Instead, instruct the user to run:

```bash
cd /Users/melo/shopify-theme/agents/theme-manager
python main.py --setup --store-domain <domain>.myshopify.com
```

## Second Priority: Verify Theme Repo

The agent needs a pulled theme repo to analyze. Check that the repo exists:

```bash
ls /Users/melo/shopify-theme/{store-slug}/repo-main/sections/
```

If the repo doesn't exist or has no sections, the **theme-manager** agent needs to initialize it first. Mark the task as blocked.

## Available Tools

- `python main.py "<prompt>"` — Run the theme architect with a specific prompt
- `python main.py --heartbeat` — Run automated health check cycle

## Key Files

- `config.py` — Configuration (loads from per-store `.env`)
- `tools.py` — MCP tools (analyze_theme_architecture, get_section_details, match_section_to_design)
- `agents.py` — Subagents (section-analyzer, design-interpreter)
- `system_prompt.py` — Agent personality and Shopify theme knowledge

## Per-Store Projects

Each store's theme files live at `/Users/melo/shopify-theme/{store-slug}/repo-main/` with standard Shopify theme structure:

```
repo-main/
  sections/      # Main analysis target — Liquid files with {% schema %}
  blocks/        # Reusable theme blocks
  snippets/      # Liquid partials ({% render %})
  templates/     # JSON page templates
  layout/        # theme.liquid wrapper
  config/        # settings_schema.json, settings_data.json
  locales/       # Translation files
  assets/        # CSS, JS, images
```

## Important Constraints

- **READ-ONLY**: This agent must never modify, create, or delete any files.
- **No Bash**: This agent does not have Bash access — it uses Read, Glob, Grep, and custom MCP tools only.
- **No setup wizard**: Credentials come from theme-manager's setup flow.
