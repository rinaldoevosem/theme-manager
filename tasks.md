# shopify-theme — tasks & decisions

## Context-bloat investigation (2026-04-10)

**Goal:** reduce the deferred-tool + skills payload loaded every turn in `/Users/melo/shopify-theme/`.

### What's loaded and why
- **Global MCP servers** (in `~/.claude.json` → `mcpServers`): `google-workspace`, `clickup`, `notebooklm-mcp`. All user-scoped, load in every project.
- **Claude.ai hosted integrations**: `mcp__claude_ai_Clickup__*`, `mcp__claude_ai_Gmail__*`, `mcp__claude_ai_Google_Calendar__*`. Configured on claude.ai, not locally. This is why ClickUp shows up **twice** in the deferred-tool list (local MCP + claude.ai hosted).
- **User plugins** (in `~/.claude/settings.json` → `enabledPlugins`): `figma@claude-plugins-official`, `agent-sdk-dev@claude-plugins-official`. **Both in active use — keep enabled.**
- **User slash commands** in `~/.claude/commands/`: `batch-from-emails.md`, `qa.md`, `upload-batch.md`, `process-errors.md`, `manual-review.md`. Unrelated batch-email workflow; load everywhere.

### Key finding: Claude Code has no per-project disable for user-scoped MCP servers
- `disabledMcpjsonServers` only applies to `.mcp.json`-sourced servers — **not** to servers configured in the global `mcpServers` block of `~/.claude.json`.
- User slash commands in `~/.claude/commands/` also have no per-project disable. They load in every project unless moved or deleted.
- Plugins **can** be overridden per-project via `enabledPlugins` in project `settings.local.json` (project scope overrides user scope).

### User constraints
- Keep **both** plugins enabled (figma + agent-sdk-dev).
- **Project-level changes only** — do not touch global state (`~/.claude.json` global `mcpServers`, `~/.claude/settings.json`, `~/.claude/commands/`).

### Decision: pending (option a vs b)
Given the constraints above, there is **no project-level-only change that actually reduces the bloat**. The only lever that works (moving the 3 MCP servers from user scope to per-project scope via `claude mcp add -s local` in the projects that use them) requires a global edit, which is outside the constraint.

**Options on the table for next session:**
- **(a)** Re-scope MCP servers: `claude mcp remove <name> -s user`, then `cd` into each consuming project and `claude mcp add <name> -s local …`. Need to know which projects use google-workspace, clickup, notebooklm-mcp.
- **(b)** Accept the bloat and do nothing. Rely on `/compact` and subagent delegation to manage context mid-session.

### What was actually changed this session
- Nothing. Global `mcpServers` removal was executed then **reverted** to respect the project-level-only constraint. Backup of `~/.claude.json` kept at `~/.claude.json.bak-20260410-090139` and the captured entries at `~/.claude/removed-mcp-servers.json` (for reference if option (a) is taken later).

### If revisiting
Start by asking: "Which projects actually use google-workspace / clickup / notebooklm-mcp?" — that unblocks option (a). Also worth checking whether the claude.ai-hosted ClickUp/Gmail/Calendar integrations can be turned off at claude.ai (they're the biggest single source of deferred-tool entries and are fully redundant with the local ClickUp MCP).

---

## Theme Designer — pending tasks

### Adobe Fonts (Typekit) integration (deferred)
**Goal:** Add Adobe Fonts as a third font source in the theme-designer's `resolve_font` tool, alongside Shopify picker and Google Fonts.

**What's needed:**
- Store `ADOBE_FONTS_PROJECT_ID` in per-store `.env` and `config.py`
- Add an `adobe_fonts` resolution strategy in the `resolve_font` tool
- Adobe Fonts loads via `<link rel="stylesheet" href="https://use.typekit.net/{PROJECT_ID}.css">`
- Font availability can't be validated without OAuth — trust the user's project config
- Update `inject_external_fonts` to handle Adobe `<link>` tags alongside Google Fonts
- Update typography-handler sub-agent prompt with Adobe Fonts workflow

**Blocked on:** User needs to provide an Adobe Fonts project ID when ready.

### Typography handler end-to-end validation
**Goal:** Re-run the full pipeline against the Fey & Co Figma design after the typography overhaul to verify MinervaModern loads via Google Fonts (or falls back correctly) and all typography scale settings are applied cleanly.

### Google Fonts dataset refresh process
**Goal:** Document and schedule periodic refresh of `data/google_fonts.json`. Currently generated via `scripts/fetch_google_fonts.py` from the google-webfonts-helper API (1938 fonts as of 2026-04-11). Should be re-run quarterly or when a missing font is reported.
