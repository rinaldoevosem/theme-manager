---
title: Shopify Theme Platform
tags: [overview]
created: 2026-04-11
updated: 2026-04-11
---

# Shopify Theme Platform

> [!info] What is this?
> A multi-agent platform that manages Shopify themes across environments, matches Figma designs to theme sections, and translates design tokens into theme settings. Orchestrated by [[infrastructure/paperclip|Paperclip]] at `localhost:3100`.

## Architecture

![[architecture-diagram#Platform Overview]]

See [[architecture-diagram]] for the full diagram with promotion flow, font resolution, and credential flow.

## Agents at a Glance

| Agent | Role | Heartbeat | Key Superpower |
|-------|------|-----------|----------------|
| [[agents/theme-manager\|Theme Manager]] | Version control & coordination | 4h | Setup wizard, PR workflow, 3-env promotion |
| [[agents/theme-architect\|Theme Architect]] | Design-to-section matcher | 6h | Section scoring algorithm (read-only) |
| [[agents/theme-designer\|Theme Designer]] | Figma-to-settings translator | 6h | 3-tier font resolution, color scheme mapping |
| [[agents/eval-runner\|Eval Runner]] | Test harness for architect | Manual | 5-dimension scoring, 40 test cases |

## Shared Infrastructure

| System | Purpose | Docs |
|--------|---------|------|
| Paperclip | Task orchestration, heartbeats, cost tracking | [[infrastructure/paperclip]] |
| Figma MCP | Design file reading across agents | [[infrastructure/figma-integration]] |
| Font Pipeline | Shopify + Google Fonts + fallback resolution | [[infrastructure/font-pipeline]] |
| Credentials | Per-store `.env` model, setup wizard | [[infrastructure/credentials-and-setup]] |

## Quick Reference

- [[reference/cli-cheatsheet]] — Every CLI command across all agents
- [[reference/env-variables]] — Complete `.env` variable reference
- [[reference/glossary]] — Platform terminology

## Repositories

| Repo | Purpose | Branch Strategy |
|------|---------|-----------------|
| `rinaldoevosem/theme-manager` | Agent source code | `main`, `dev/theme-designer` |
| `rinaldoevosem/horizon-clone` | Shopify theme (per-store) | `main`, `staging`, `dev` |

## Tech Stack

- **Language**: Python 3.14
- **Agent SDK**: `claude-agent-sdk >= 0.1.56`
- **Model**: Claude Sonnet (default), configurable to Opus via `--model`
- **Auth**: Claude subscription via CLI (not API keys)
- **Environments**: Per-agent `.venv` virtual environments
- **Orchestration**: Paperclip REST API at `localhost:3100`

## How the Pieces Fit Together

```
1. User provides a Shopify store domain
   └─ Theme Manager runs --setup wizard
      └─ Saves credentials to {store-slug}/.env
      └─ Pulls theme, initializes GitHub repo

2. Design review (Figma design provided)
   └─ Theme Architect analyzes the theme structure
      └─ Matches design sections to existing theme sections (read-only)

3. Design implementation
   └─ Theme Designer reads Figma tokens (fonts, colors, typography)
      └─ Maps to theme settings, writes settings_data.json

4. Quality assurance
   └─ Eval Runner scores the architect's accuracy
      └─ Generates improvement feedback
```
