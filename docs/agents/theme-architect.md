---
title: Theme Architect
tags: [agent, theme-architect]
created: 2026-04-11
updated: 2026-04-11
---

# Theme Architect

> [!info] Read-only Shopify theme architecture expert. Analyzes theme code and Figma designs to recommend which existing section(s) best fit a given design. Never modifies files.

## Overview

| Property | Value |
|----------|-------|
| **Agent ID** | `79f078a4-3d41-4bc1-bd58-041b93a9f015` |
| **Model** | Sonnet (default), configurable via `--model` or `THEME_ARCHITECT_MODEL` |
| **Heartbeat** | Every 6 hours (`0 */6 * * *`) |
| **Budget** | $30/month |
| **Permissions** | Read, Glob, Grep (read-only — no Bash, no Write) |
| **Directory** | `agents/theme-architect/` |

## Sub-Agents

| Sub-Agent | Purpose | Tools |
|-----------|---------|-------|
| **section-analyzer** | Deep-dives into a specific section's Liquid code, block types, settings schema, and snippet dependencies. | Read, Glob, Grep, `get_section_details` |
| **design-interpreter** | Interprets Figma designs and extracts structured requirements — layout type, block types, settings, interactive elements. | Read, `get_design_context`, `get_screenshot`, `get_metadata` |

## MCP Tools

| Tool | Description |
|------|-------------|
| `analyze_theme_architecture` | Scan theme directory and return structured overview — sections, blocks, templates, snippets |
| `get_section_details` | Parse a section file's `{% schema %}`, blocks, settings, and snippet dependencies |
| `match_section_to_design` | Score existing sections against design requirements (blocks 50%, settings 30%, layout 20%) |

## CLI Usage

```bash
# Run with a prompt
python main.py "Analyze the full theme architecture"

# Heartbeat mode (automated task processing)
python main.py --heartbeat

# Override model (e.g. use Opus for complex analysis)
python main.py --model claude-opus-4-6 "Match this design to existing sections"
```

> [!tip] Model Override
> For complex Figma-to-section matching, override to Opus: `--model claude-opus-4-6` or set `THEME_ARCHITECT_MODEL=claude-opus-4-6` in `.env`.

## Section Scoring Algorithm

When matching a design to existing sections, `match_section_to_design` scores candidates across three dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| Block types | 50% | How many required block types the section supports |
| Settings | 30% | How many required settings the section exposes |
| Layout | 20% | How well the section's layout matches the design |

## Paperclip Commands

| Command | Description |
|---------|-------------|
| `analyze-theme` | Full architectural overview of the theme |
| `match-design` | Match a Figma design to existing sections |
| `section-detail` | Deep-dive into a specific section |
| `design-requirements` | Extract requirements from a design description |

## Dependencies

> [!warning] Requires Theme Manager Setup
> This agent does not have its own setup wizard. It reads `.env` files created by [[agents/theme-manager|Theme Manager]]'s `--setup` command. If credentials are missing, run `cd ../theme-manager && python main.py --setup --store-domain <domain>`.

Also requires:
- A pulled theme repo at `{store-slug}/repo-main/` (initialized by Theme Manager)
- [[infrastructure/figma-integration|Figma MCP]] for design interpretation

## Evaluation

The [[agents/eval-runner|Eval Runner]] test harness scores this agent across 40 test cases and 5 dimensions. See [[agents/eval-runner]] for the scoring methodology and baseline results.

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — handles `--heartbeat`, `--model`, prompt modes |
| `config.py` | Configuration — loads per-store `.env` |
| `tools.py` | MCP server — 3 custom tools with scoring logic |
| `agents.py` | Sub-agent definitions (section-analyzer, design-interpreter) |
| `system_prompt.py` | Shopify theme knowledge and analysis workflow |
| `paperclip_client.py` | Async HTTP client for Paperclip API |
| `paperclip_agent.json` | Agent metadata and heartbeat schedule |
