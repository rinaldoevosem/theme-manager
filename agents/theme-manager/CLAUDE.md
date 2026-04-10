# Shopify Theme Manager — Agent Instructions

## First Priority: Credential Check

Before doing ANY work, verify that `.env` has real credentials (not placeholders):

```bash
grep -E "^(SHOPIFY_ACCESS_TOKEN|GITHUB_TOKEN|GITHUB_OWNER)=" .env
```

If any of these values are empty, missing, or contain `dry-run-token`, **you must launch the setup wizard before proceeding**.

### Launching the Setup Wizard

1. Extract the store domain from your task (look for `*.myshopify.com` in the title or description).
2. Run the wizard with the store domain:

```bash
python main.py --setup --store-domain <domain>
```

For example: `python main.py --setup --store-domain horizon-clone.myshopify.com`

This opens a browser window where the user authenticates with Shopify and GitHub, selects repositories, and picks themes. The command blocks until setup is complete.

3. After the wizard finishes, re-read `.env` to confirm credentials are now valid.
4. If credentials are still missing (user closed the wizard without saving), mark the task as blocked with a clear message explaining what credentials are needed.
5. If credentials are valid, proceed with the task.

### Per-Store Projects

Each store gets its own project directory at `/Users/melo/shopify-theme/{store-slug}/` (e.g., `horizon-clone`). When `--store-domain` is provided, the wizard saves `.env` to the store's project directory instead of the theme-manager directory.

## Second Priority: Initialize Empty GitHub Repo

After credentials are verified, check the configured GitHub repo (`GITHUB_REPO`). If it's empty (no commits), pull the Shopify theme and push it as the initial commit on `main`.

### How to check if the repo is empty

```bash
source /Users/melo/shopify-theme/{store-slug}/.env
gh api repos/$GITHUB_OWNER/$GITHUB_REPO/commits --jq 'length' 2>/dev/null || echo "0"
```

If the result is `0` or the API returns a "Git Repository is empty" error, the repo needs initialization.

### How to initialize the repo from a Shopify theme

```bash
STORE_DIR="/Users/melo/shopify-theme/{store-slug}"
source "$STORE_DIR/.env"

# Clone the empty repo
git clone "https://github.com/$GITHUB_OWNER/$GITHUB_REPO.git" "$STORE_DIR/repo"
cd "$STORE_DIR/repo"

# Pull theme files from Shopify
shopify theme pull --store "$SHOPIFY_STORE_DOMAIN" --theme "$SHOPIFY_THEME_ID_MAIN" --path . --password "$SHOPIFY_ACCESS_TOKEN"

# Commit and push
git add -A
git commit -m "Initial theme import from Shopify ($SHOPIFY_STORE_DOMAIN, theme $SHOPIFY_THEME_ID_MAIN)"
git push origin main
```

**Important:**
- Always use `--password` flag with the Shopify access token for CLI auth
- If `git push` fails because the default branch is `master` instead of `main`, check with `git branch` and push to the correct branch
- Post a comment on the task after the repo is initialized, listing the files pushed
- If the repo doesn't exist yet, do NOT create it — report it and mark as blocked
- **Do NOT mark the task as done yet** — proceed to Third Priority (create staging & dev branches) first

## Third Priority: Create Staging & Dev Branches

**Immediately after** the main branch is initialized (or if it already has commits), create `staging` and `dev` branches if they don't exist. Do this in the same task — do NOT wait for a separate task or user confirmation.

All three environments share **one repo, three branches**: `main`, `staging`, `dev`.

### How to check if branches exist

```bash
source /Users/melo/shopify-theme/{store-slug}/.env
gh api repos/$GITHUB_OWNER/$GITHUB_REPO/branches/staging --jq '.name' 2>/dev/null
gh api repos/$GITHUB_OWNER/$GITHUB_REPO/branches/dev --jq '.name' 2>/dev/null
```

### Create missing branches from main

```bash
# Get main branch HEAD SHA
SHA=$(gh api repos/$GITHUB_OWNER/$GITHUB_REPO/git/refs/heads/main --jq '.object.sha')

# Create staging branch (if missing)
gh api repos/$GITHUB_OWNER/$GITHUB_REPO/git/refs -f ref="refs/heads/staging" -f sha="$SHA"

# Create dev branch (if missing)
gh api repos/$GITHUB_OWNER/$GITHUB_REPO/git/refs -f ref="refs/heads/dev" -f sha="$SHA"
```

After creating branches, post a comment on the task:
> Created `staging` and `dev` branches from main (SHA: {sha}). Please connect each branch to its corresponding Shopify theme in the Shopify Admin.

**Do NOT create Shopify themes** — the user will connect branches to themes manually in the Shopify Admin.

## Theme Management

This agent manages Shopify themes across three branches (`dev`, `staging`, `main`) in a single GitHub repo. Each branch is connected to its own Shopify theme. See `system_prompt.py` for the full promotion workflow and rules.

### Available Tools

- `python main.py "<prompt>"` — Run the theme manager agent with a specific prompt
- `python main.py --setup` — Launch the setup wizard (no store pre-fill)
- `python main.py --setup --store-domain <domain>` — Launch wizard for a specific store
- `python main.py --heartbeat` — Run automated health check cycle

### Key Files

- `config.py` — Configuration (loads from `.env`)
- `tools.py` — MCP tools (get_theme_status, check_promotion_readiness, generate_change_summary)
- `agents.py` — Subagents (sync-checker, pr-reviewer, stakeholder-reporter)
- `setup_server.py` — Browser-based setup wizard
