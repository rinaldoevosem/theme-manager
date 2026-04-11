# Shopify Theme Designer — Agent Instructions

## Overview

This agent translates Figma design guidelines into Shopify theme settings. It reads design tokens from Figma (fonts, colors, typography scale, button styles) and maps them to `settings_data.json` values. It **only modifies theme settings** — never sections, templates, or schema files.

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

The agent needs a pulled theme repo with settings files. Check:

```bash
ls /Users/melo/shopify-theme/{store-slug}/repo-main/config/settings_schema.json
ls /Users/melo/shopify-theme/{store-slug}/repo-main/config/settings_data.json
```

If the repo doesn't exist or settings are missing, the **theme-manager** agent needs to initialize it first. Mark the task as blocked.

## Available Commands

```bash
# Run with a specific prompt
python main.py "Apply design tokens from this Figma file: <url>"

# Run automated heartbeat cycle
python main.py --heartbeat

# Preview changes without writing (dry run)
python main.py --dry-run "Apply design tokens from <url>"

# Override model
python main.py --model claude-opus-4-6 "Apply design tokens from <url>"
```

## Key Files

- `config.py` — Configuration (loads from per-store `.env`)
- `tools.py` — MCP tools (parse_settings_schema, get_shopify_fonts, validate_setting_value, apply_design_tokens)
- `agents.py` — Subagents (figma-interpreter)
- `system_prompt.py` — Agent personality and Shopify settings domain knowledge

## Per-Store Projects

Each store's theme files live at `/Users/melo/shopify-theme/{store-slug}/repo-main/` with standard Shopify theme structure. The agent specifically operates on:

```
repo-main/
  config/
    settings_schema.json  # READ-ONLY — defines what settings exist
    settings_data.json    # MODIFIED — current setting values
```

## Important Constraints

- **Only modifies `settings_data.json`** under the `current` key.
- **Never touches `settings_schema.json`** — it defines the schema.
- **Never modifies `presets`** in settings_data.json.
- **Always creates a `.backup`** before writing changes.
- **No git operations** — leave commits and promotion to the theme-manager agent.
- **Validates all values** against the schema before writing (select options, range bounds, font identifiers).
