---
title: Theme Designer
tags: [agent, theme-designer]
created: 2026-04-11
updated: 2026-04-11
---

# Theme Designer

> [!info] Translates Figma design guidelines (fonts, colors, typography, buttons) into Shopify theme settings. Only modifies `settings_data.json` — never sections, templates, or schema files.

## Overview

| Property | Value |
|----------|-------|
| **Agent ID** | `a7e3b1c4-5f92-4d8a-b6e1-2c9d0f3a8b57` |
| **Model** | Sonnet (default), configurable via `--model` or `THEME_DESIGNER_MODEL` |
| **Heartbeat** | Every 6 hours (`0 */6 * * *`) |
| **Budget** | $40/month |
| **Permissions** | Read, Write, Glob, Grep (writes only to settings + snippets) |
| **Directory** | `agents/theme-designer/` |

## Sub-Agents

| Sub-Agent | Purpose | Tools |
|-----------|---------|-------|
| **figma-interpreter** | Extracts structured design tokens from Figma — fonts, colors, typography scale, buttons, spacing. Returns a JSON object with `fonts`, `colors`, `typography_scale`, `buttons`, `spacing`, `unmapped_tokens`. | Read, `get_design_context`, `get_screenshot`, `get_metadata` |
| **typography-handler** | Resolves fonts against Shopify picker / Google Fonts / fallback. Maps typography scale to theme settings. Returns `font_changes`, `typography_changes`, `external_fonts`. | Read, Glob, Grep, `parse_settings_schema`, `resolve_font`, `validate_setting_value` |

## MCP Tools

| Tool | Description |
|------|-------------|
| `parse_settings_schema` | Parse `settings_schema.json` and summarize all configurable settings with types, options, and current values |
| `resolve_font` | Resolve a font family against 3 sources: Shopify picker (76), Google Fonts (1938), classification fallback |
| `validate_setting_value` | Validate a proposed value against schema constraints (select options, range bounds, font identifiers) |
| `apply_design_tokens` | Apply validated changes to `settings_data.json` with backup and detailed change reporting |
| `inject_external_fonts` | Create Liquid snippets for external fonts (Google Fonts CDN) and modify layout files |
| `get_shopify_fonts` | Look up Shopify's built-in font library (76 fonts with weights/styles) |

## CLI Usage

```bash
# Apply design from Figma
python main.py "Apply the design tokens from this Figma file: <url>"

# Dry run (preview changes without writing)
python main.py --dry-run "Apply design tokens from <url>"

# Heartbeat mode
python main.py --heartbeat

# Override model
python main.py --model claude-opus-4-6 "Apply design tokens from <url>"
```

> [!tip] Dry Run Mode
> Use `--dry-run` to preview all proposed changes without modifying `settings_data.json`. The agent uses `parse_settings_schema` and `validate_setting_value` to preview mapping decisions without calling `apply_design_tokens`.

## Core Workflow

```
1. Receive Figma design URL
2. Delegate to figma-interpreter → extract design tokens
3. Parse theme schema → understand available settings
4. Delegate to typography-handler → resolve fonts + map scale
5. Map remaining tokens → colors, buttons, layout
6. Handle external fonts → create Liquid snippets if needed
7. Apply changes → write to settings_data.json with backup
8. Report → detailed change report
```

## Color Mapping Strategy

- Map design schemes **sequentially** to scheme-1, scheme-2, scheme-3 (never skip)
- Map palette roles: background, foreground_heading, foreground, primary, border, shadow
- Derive missing values: darken by ~10% for hover, foreground at reduced opacity for borders
- See system prompt for full mapping rules

## Font Resolution

Uses a 3-tier resolution strategy. See [[infrastructure/font-pipeline|Font Pipeline]] for details.

1. **Shopify picker** (76 fonts) — native `font_picker` identifier
2. **Google Fonts** (1938 fonts) — external loading via CDN + Shopify fallback
3. **Classification fallback** — best visual match from Shopify picker

## Data Files

| File | Description |
|------|-------------|
| `data/google_fonts.json` | 1938 Google Fonts with category, weights, classification, CSS URLs (763 KB) |
| `scripts/fetch_google_fonts.py` | Fetches from google-webfonts-helper API, generates the dataset |

> [!warning] Quarterly Refresh
> The Google Fonts dataset should be refreshed quarterly or when a missing font is reported. Run `python scripts/fetch_google_fonts.py` to regenerate `data/google_fonts.json`.

## Dependencies

> [!warning] Requires Theme Manager Setup
> This agent reads `.env` files created by [[agents/theme-manager|Theme Manager]]'s `--setup` command. If credentials are missing, run `cd ../theme-manager && python main.py --setup --store-domain <domain>`.

Also requires:
- A pulled theme repo with `config/settings_schema.json` and `config/settings_data.json`
- [[infrastructure/figma-integration|Figma MCP]] for design token extraction

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — handles `--heartbeat`, `--dry-run`, `--model`, prompt modes |
| `config.py` | Configuration — loads per-store `.env` |
| `tools.py` | MCP server — 6 custom tools, font classifications, Google Fonts loader |
| `agents.py` | Sub-agent definitions (figma-interpreter, typography-handler) |
| `system_prompt.py` | Settings architecture, color/font mapping rules |
| `data/google_fonts.json` | Google Fonts dataset (1938 fonts) |
| `scripts/fetch_google_fonts.py` | Dataset refresh script |
| `paperclip_client.py` | Async HTTP client for Paperclip API |
| `paperclip_agent.json` | Agent metadata and heartbeat schedule |
