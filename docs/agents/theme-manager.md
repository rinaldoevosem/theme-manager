---
title: Theme Manager
tags: [agent, theme-manager]
created: 2026-04-11
updated: 2026-04-11
---

# Theme Manager

> [!info] Manages Shopify theme version control across `dev`, `staging`, and `main` environments. Monitors sync status, reviews PRs for promotion workflow, and generates stakeholder reports.

## Overview

| Property | Value |
|----------|-------|
| **Agent ID** | `theme-manager` |
| **Model** | Sonnet (SDK default) |
| **Heartbeat** | Every 4 hours (`0 */4 * * *`) |
| **Budget** | $50/month |
| **Permissions** | Read, Write, Edit, Glob, Grep, Bash, WebFetch |
| **Directory** | `agents/theme-manager/` |

## Sub-Agents

| Sub-Agent | Purpose | Tools |
|-----------|---------|-------|
| **sync-checker** | Detects drift between Shopify themes and GitHub repos. Identifies uncommitted customizer changes. | Bash, Read, Glob, Grep, `get_theme_status` |
| **pr-reviewer** | Reviews PRs for correct promotion path (dev -> staging -> main), required metadata, and breaking changes. | Bash, Read, Glob, Grep, `check_promotion_readiness` |
| **stakeholder-reporter** | Generates technical reports for the dev team and non-technical reports for clients. | Bash, Read, Grep, `get_theme_status`, `generate_change_summary` |

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_theme_status` | Get status of a Shopify theme — last deployed, file count, modification date |
| `check_promotion_readiness` | Verify if an environment is ready to promote to the next stage |
| `generate_change_summary` | Format technical changes into stakeholder-friendly reports |

## CLI Usage

```bash
# Run with a prompt
python main.py "Give me a full status report of all three environments"

# Heartbeat mode (automated health check)
python main.py --heartbeat

# Launch browser-based setup wizard
python main.py --setup

# Setup for a specific store
python main.py --setup --store-domain horizon-clone.myshopify.com
```

## Setup Wizard

The Theme Manager includes a browser-based setup wizard (`setup_server.py`) that:

1. Opens a local HTTP server
2. User authenticates with Shopify (OAuth) and GitHub (OAuth)
3. User selects GitHub repo and Shopify themes for main/staging/dev
4. Saves credentials to `{store-slug}/.env`

> [!warning] Gateway Agent
> The Theme Manager's setup wizard creates the `.env` files that [[agents/theme-architect|Theme Architect]] and [[agents/theme-designer|Theme Designer]] depend on. Always run setup here first.

## Promotion Workflow

See [[architecture-diagram#Theme Promotion Flow]] for the visual flow.

1. **dev -> staging**: Requires PR with test plan
2. **staging -> main**: Requires PR with client approval
3. **Direct pushes to main**: Blocked by convention

## Paperclip Commands

| Command | Description |
|---------|-------------|
| `status` | Get current status of all environments |
| `check-sync` | Detect drift between GitHub and Shopify |
| `review-prs` | Review all open theme PRs |
| `client-report` | Generate non-technical client report |
| `team-report` | Generate technical team report |
| `promote` | Start dev -> staging promotion |

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — builds agent options, handles CLI flags |
| `config.py` | Configuration — `ThemeEnvironment` dataclass, multi-env config |
| `tools.py` | MCP server — 3 custom tools |
| `agents.py` | Sub-agent definitions (3 sub-agents) |
| `system_prompt.py` | Agent personality and promotion rules |
| `setup_server.py` | Browser-based OAuth setup wizard |
| `paperclip_client.py` | Async HTTP client for Paperclip API |
| `paperclip_agent.json` | Agent metadata and heartbeat schedule |

## Configuration

See [[reference/env-variables]] for the complete variable reference.

Key variables: `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_ACCESS_TOKEN`, `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`, `SHOPIFY_THEME_ID_MAIN`, `SHOPIFY_THEME_ID_STAGING`, `SHOPIFY_THEME_ID_DEV`.
