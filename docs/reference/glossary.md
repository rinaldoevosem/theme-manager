---
title: Glossary
tags: [reference]
created: 2026-04-11
updated: 2026-04-11
---

# Glossary

## Agents & Orchestration

| Term | Definition |
|------|-----------|
| **Heartbeat** | Scheduled cron job where an agent wakes up, fetches tasks from [[infrastructure/paperclip\|Paperclip]], processes them, and reports results. Each agent has its own interval (4h or 6h). |
| **Sub-agent** | A specialized agent invoked by a parent agent via the `Agent` tool. Has its own prompt and tool access but runs within the parent's session. |
| **MCP tool** | A tool exposed via the Model Context Protocol. Custom tools are defined in each agent's `tools.py` using `create_sdk_mcp_server`. |
| **Paperclip** | The task orchestration REST API at `localhost:3100`. Routes tasks to agents, tracks status, records costs. |
| **Agent SDK** | `claude-agent-sdk` — Anthropic's Python SDK for building LLM agents with tools, sub-agents, and MCP servers. |

## Shopify Theme

| Term | Definition |
|------|-----------|
| **Section** | A reusable, configurable component in a Shopify theme (e.g. hero banner, product grid). Defined as a Liquid file with a `{% schema %}` block. |
| **Block** | A sub-component within a section. Sections define which block types they support. |
| **Snippet** | A reusable Liquid partial included via `{% render 'snippet-name' %}`. |
| **Template** | A JSON file defining which sections appear on a page type (e.g. `product.json`, `collection.json`). |
| **settings_schema.json** | Defines all available theme settings — their types, valid options, defaults. Read-only. |
| **settings_data.json** | Contains the current values for all theme settings. Has a `current` key (active values) and a `presets` key (read-only). |
| **Preset** | A saved configuration snapshot in `settings_data.json`. The `current` key holds the active preset's values. |

## Font System

| Term | Definition |
|------|-----------|
| **font_picker** | A Shopify setting type that only accepts identifiers from Shopify's built-in font library (~76 fonts). Format: `{slug}_{style}{weight}` (e.g. `jost_n4`). |
| **Font identifier** | A Shopify font picker value. `n` = normal, `i` = italic. The digit is the weight/100 (4 = 400, 7 = 700). |
| **Dual-track strategy** | For external fonts: set `font_picker` to a Shopify fallback AND create Liquid snippets that load the real font via CDN. |
| **Font classification** | A category describing a font's visual character (e.g. `geometric_sans`, `serif_display`, `neo_grotesque`). Used for intelligent fallback matching. |
| **External font** | A font not in Shopify's picker but available via Google Fonts CDN. Loaded via `custom-fonts.liquid` snippet. |
| **Font role** | One of four theme font slots: `body`, `heading`, `subheading`, `accent`. Each maps to a CSS custom property. |

## Theme Operations

| Term | Definition |
|------|-----------|
| **Promotion** | Moving changes from one environment to the next: `dev` -> `staging` -> `main`. Enforced via PR workflow. |
| **Drift** | When a Shopify theme's live state diverges from its GitHub branch — usually from manual Shopify Customizer edits. |
| **Color scheme** | A named set of ~30 color properties in `settings_data.json` (e.g. `scheme-1`). Sections reference schemes by number. |
| **Design token** | A discrete visual value extracted from a Figma design: a color hex, a font family, a heading size, etc. |
| **Typography scale** | The set of heading sizes (H1-H6), line heights, letter spacing, and text transforms defined in a design. |

## Evaluation

| Term | Definition |
|------|-----------|
| **Eval case** | A single test scenario defined in YAML: a design description, expected section matches, and difficulty rating. |
| **Suite** | A group of related eval cases (e.g. `hero-sections`, `product-sections`). |
| **Composite score** | The weighted average of accuracy (40%), reasoning (25%), completeness (15%), cost (10%), and speed (10%). |
| **Baseline** | The first eval run results used as a benchmark. Current: 90% pass rate, ~$0.38 avg cost (2026-04-09). |

## Environment

| Term | Definition |
|------|-----------|
| **Store slug** | The subdomain from a `*.myshopify.com` domain, used as the project directory name (e.g. `horizon-clone`). |
| **Per-store project** | The directory at `{store-slug}/` containing `.env`, pulled theme repo, and optional analyzers. |
| **Three-branch model** | `main` (production), `staging` (client review), `dev` (active development). All in one GitHub repo. |
