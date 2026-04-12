---
title: Environment Variables
tags: [reference, credentials]
created: 2026-04-11
updated: 2026-04-11
---

# Environment Variables

All `.env` files are gitignored. Per-store credentials live at `{store-slug}/.env`; per-agent config lives at `agents/<agent>/.env`.

## Per-Store Credentials (`{store-slug}/.env`)

Created by the [[agents/theme-manager|Theme Manager]] setup wizard. Read by all 3 LLM agents.

| Variable | Required | Description |
|----------|----------|-------------|
| `SHOPIFY_STORE_DOMAIN` | Yes | e.g. `horizon-clone.myshopify.com` |
| `SHOPIFY_ACCESS_TOKEN` | Yes | Shopify Admin API access token (from OAuth) |
| `GITHUB_TOKEN` | Yes | GitHub personal access token (from OAuth) |
| `GITHUB_OWNER` | Yes | GitHub username or org, e.g. `rinaldoevosem` |
| `GITHUB_REPO` | Yes | GitHub repo name, e.g. `horizon-clone` |
| `SHOPIFY_THEME_ID_MAIN` | Yes | Shopify theme ID for the `main` branch |
| `SHOPIFY_THEME_ID_STAGING` | Yes | Shopify theme ID for the `staging` branch |
| `SHOPIFY_THEME_ID_DEV` | Yes | Shopify theme ID for the `dev` branch |

## Paperclip Configuration

Present in each agent's `.env` or the store's `.env`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAPERCLIP_API_URL` | No | `http://localhost:3100` | Paperclip REST API base URL |
| `PAPERCLIP_API_KEY` | No | None | API key (unused in local dev) |
| `PAPERCLIP_COMPANY_ID` | Yes* | — | Company ID for task routing |
| `PAPERCLIP_AGENT_ID` | No | Agent-specific default | Agent ID override |

> [!info] *`PAPERCLIP_COMPANY_ID` is required for heartbeat mode but optional for direct prompt usage.

## Agent-Specific Variables

### Theme Manager

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAPERCLIP_AGENT_ID` | No | `theme-manager` | Override agent ID |

### Theme Architect

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAPERCLIP_AGENT_ID` | No | `theme-architect` | Override agent ID |
| `THEME_ARCHITECT_MODEL` | No | SDK default (Sonnet) | Model override (e.g. `claude-opus-4-6`) |
| `SHOPIFY_DEV_MCP_PATH` | No | None | Path to Node.js Shopify Dev MCP server |

### Theme Designer

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAPERCLIP_AGENT_ID` | No | `theme-designer` | Override agent ID |
| `THEME_DESIGNER_MODEL` | No | SDK default (Sonnet) | Model override (e.g. `claude-opus-4-6`) |
| `SHOPIFY_DEV_MCP_PATH` | No | None | Path to Node.js Shopify Dev MCP server |

### Eval Runner

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAPERCLIP_API_URL` | No | `http://localhost:3100` | Paperclip API URL |
| `PAPERCLIP_COMPANY_ID` | Yes | — | Company ID for task creation |
| `ARCHITECT_AGENT_ID` | Yes | — | Agent ID of the theme-architect |
| `ARCHITECT_DIR` | Yes | — | Path to `agents/theme-architect/` |
| `THEME_DIR` | Yes | — | Path to theme repo for context |
| `EVAL_RUNNER_AGENT_ID` | No | — | Optional: eval runner's own agent ID |
| `MAX_CASES` | No | `40` | Maximum eval cases per run |
| `TIMEOUT_PER_CASE_MIN` | No | `3` | Timeout per case in minutes |

## Model Override Precedence

For agents that support model configuration:

```
--model flag  >  THEME_*_MODEL env var  >  SDK default (Sonnet)
```

## Example `.env`

```env
# Per-store credentials (horizon-clone/.env)
SHOPIFY_STORE_DOMAIN=horizon-clone.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
GITHUB_TOKEN=ghp_xxxxx
GITHUB_OWNER=rinaldoevosem
GITHUB_REPO=horizon-clone
SHOPIFY_THEME_ID_MAIN=123456789
SHOPIFY_THEME_ID_STAGING=987654321
SHOPIFY_THEME_ID_DEV=111222333

# Paperclip
PAPERCLIP_API_URL=http://localhost:3100
PAPERCLIP_COMPANY_ID=your-company-id
```

> [!warning] Security
> Never commit `.env` files. All are gitignored. Token values shown above are placeholders.
