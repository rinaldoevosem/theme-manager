"""Browser-based setup wizard for the Shopify Theme Manager.

Launches a local web server with a step-by-step wizard that authenticates
with Shopify and GitHub, lets the user pick repos and themes, and writes
the resulting configuration to .env.

Usage:
    python main.py --setup
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import webbrowser
from pathlib import Path

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

PORT = 8420
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"

# Prefill data for auto-launched wizard
_prefill_domain: str = ""

# In-memory session state (single user, localhost only)
_state: dict[str, str] = {
    "shopify_domain": "",
    "shopify_token": "",
    "github_token": "",
    "github_login": "",
}


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

async def shopify_verify(request: Request) -> JSONResponse:
    body = await request.json()
    domain = body.get("domain", "").strip().rstrip("/")
    token = body.get("token", "").strip()

    if not domain or not token:
        return JSONResponse({"ok": False, "error": "Domain and token are required."})

    # Normalize domain
    if domain.startswith("https://"):
        domain = domain.removeprefix("https://")
    if domain.startswith("http://"):
        domain = domain.removeprefix("http://")
    if not domain.endswith(".myshopify.com"):
        domain = domain.split(".")[0] + ".myshopify.com"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{domain}/admin/api/2024-10/shop.json",
                headers={"X-Shopify-Access-Token": token},
                timeout=10,
            )
        if resp.status_code == 200:
            shop = resp.json()["shop"]
            _state["shopify_domain"] = domain
            _state["shopify_token"] = token
            return JSONResponse({"ok": True, "shop_name": shop["name"], "domain": domain})
        return JSONResponse({"ok": False, "error": f"Shopify returned HTTP {resp.status_code}."})
    except httpx.ConnectError:
        return JSONResponse({"ok": False, "error": f"Could not connect to {domain}."})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


async def github_verify_pat(request: Request) -> JSONResponse:
    body = await request.json()
    token = body.get("token", "").strip()
    if not token:
        return JSONResponse({"ok": False, "error": "Token is required."})

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                timeout=10,
            )
        if resp.status_code == 200:
            user = resp.json()
            _state["github_token"] = token
            _state["github_login"] = user["login"]
            return JSONResponse({"ok": True, "login": user["login"], "name": user.get("name", "")})
        return JSONResponse({"ok": False, "error": f"GitHub returned HTTP {resp.status_code}."})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


async def github_device_flow_start(request: Request) -> JSONResponse:
    body = await request.json()
    client_id = body.get("client_id", "").strip()
    if not client_id:
        return JSONResponse({"ok": False, "error": "Client ID is required."})

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://github.com/login/device/code",
                data={"client_id": client_id, "scope": "repo"},
                headers={"Accept": "application/json"},
                timeout=10,
            )
        data = resp.json()
        if "device_code" in data:
            return JSONResponse({"ok": True, **data})
        return JSONResponse({"ok": False, "error": data.get("error_description", "Unknown error")})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


async def github_device_flow_poll(request: Request) -> JSONResponse:
    body = await request.json()
    client_id = body.get("client_id", "").strip()
    device_code = body.get("device_code", "").strip()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
        data = resp.json()
        if "access_token" in data:
            token = data["access_token"]
            _state["github_token"] = token
            # Fetch user info
            user_resp = await httpx.AsyncClient().get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                timeout=10,
            )
            login = user_resp.json().get("login", "") if user_resp.status_code == 200 else ""
            _state["github_login"] = login
            return JSONResponse({"status": "complete", "login": login})
        error = data.get("error", "")
        if error in ("authorization_pending", "slow_down"):
            return JSONResponse({"status": "pending"})
        return JSONResponse({"status": "error", "error": data.get("error_description", error)})
    except Exception as exc:
        return JSONResponse({"status": "error", "error": str(exc)})


async def github_orgs(request: Request) -> JSONResponse:
    token = _state.get("github_token", "")
    if not token:
        return JSONResponse({"ok": False, "error": "Not authenticated."})

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user/orgs",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                timeout=10,
            )
        orgs = [o["login"] for o in resp.json()] if resp.status_code == 200 else []
        return JSONResponse({"ok": True, "orgs": orgs, "user": _state.get("github_login", "")})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


async def github_repos(request: Request) -> JSONResponse:
    token = _state.get("github_token", "")
    if not token:
        return JSONResponse({"ok": False, "error": "Not authenticated."})

    owner = request.query_params.get("owner", _state.get("github_login", ""))
    all_repos: list[dict] = []

    try:
        async with httpx.AsyncClient() as client:
            # Fetch up to 3 pages (300 repos)
            for page in range(1, 4):
                resp = await client.get(
                    f"https://api.github.com/users/{owner}/repos",
                    params={"per_page": 100, "page": page, "sort": "updated", "type": "all"},
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                    timeout=10,
                )
                if resp.status_code != 200:
                    break
                repos = resp.json()
                if not repos:
                    break
                for r in repos:
                    all_repos.append({
                        "name": r["name"],
                        "full_name": r["full_name"],
                        "description": r.get("description") or "",
                        "private": r["private"],
                    })
        return JSONResponse({"ok": True, "repos": all_repos})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


async def shopify_themes(request: Request) -> JSONResponse:
    domain = _state.get("shopify_domain", "")
    token = _state.get("shopify_token", "")
    if not domain or not token:
        return JSONResponse({"ok": False, "error": "Not authenticated with Shopify."})

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{domain}/admin/api/2024-10/themes.json",
                headers={"X-Shopify-Access-Token": token},
                timeout=10,
            )
        if resp.status_code == 200:
            themes = [
                {"id": t["id"], "name": t["name"], "role": t["role"]}
                for t in resp.json()["themes"]
            ]
            return JSONResponse({"ok": True, "themes": themes})
        return JSONResponse({"ok": False, "error": f"Shopify returned HTTP {resp.status_code}."})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


async def get_prefill(request: Request) -> JSONResponse:
    """Return prefill data for auto-launched wizard."""
    return JSONResponse({
        "domain": _prefill_domain,
        "project_dir": str(ENV_PATH.parent),
    })


async def save_config(request: Request) -> JSONResponse:
    body = await request.json()

    # Read existing .env to preserve Paperclip settings
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, v = stripped.split("=", 1)
                existing[k.strip()] = v.strip()

    # For new project dirs, inherit Paperclip settings from the agent's own .env
    agent_env = BASE_DIR / ".env"
    if not existing.get("PAPERCLIP_API_URL") and agent_env.exists() and agent_env != ENV_PATH:
        for line in agent_env.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, v = stripped.split("=", 1)
                if k.strip().startswith("PAPERCLIP_") and k.strip() not in existing:
                    existing[k.strip()] = v.strip()

    env_content = f"""\
# Generated by Theme Manager setup wizard

# Shopify
SHOPIFY_STORE_DOMAIN={_state['shopify_domain']}
SHOPIFY_ACCESS_TOKEN={_state['shopify_token']}

# GitHub
GITHUB_TOKEN={_state['github_token']}
GITHUB_OWNER={body['github_owner']}

# Theme repository (single repo, branches: main, staging, dev)
GITHUB_REPO={body['repo']}

# Shopify Theme IDs
SHOPIFY_THEME_ID_MAIN={body['themes']['main']}
SHOPIFY_THEME_ID_STAGING={body['themes']['staging']}
SHOPIFY_THEME_ID_DEV={body['themes']['dev']}

# Paperclip integration
PAPERCLIP_API_URL={existing.get('PAPERCLIP_API_URL', 'http://localhost:3100')}
PAPERCLIP_AGENT_ID={existing.get('PAPERCLIP_AGENT_ID', 'theme-manager')}
PAPERCLIP_COMPANY_ID={existing.get('PAPERCLIP_COMPANY_ID', '')}
PAPERCLIP_API_KEY={existing.get('PAPERCLIP_API_KEY', '')}
"""

    ENV_PATH.write_text(env_content)

    # Schedule server shutdown
    loop = asyncio.get_event_loop()
    loop.call_later(1.5, lambda: os.kill(os.getpid(), signal.SIGTERM))

    return JSONResponse({"ok": True, "path": str(ENV_PATH)})


# ---------------------------------------------------------------------------
# Frontend (inline SPA)
# ---------------------------------------------------------------------------

async def homepage(request: Request) -> HTMLResponse:
    return HTMLResponse(WIZARD_HTML)


WIZARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Theme Manager Setup</title>
<style>
:root {
  --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280;
  --accent: #5c6ac4; --accent-hover: #4a58b0;
  --success: #008060; --error: #d72c0d;
  --border: #e1e3e5; --input-bg: #f6f6f7;
  --card-bg: #ffffff; --card-shadow: 0 1px 3px rgba(0,0,0,0.08);
  --radius: 8px;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111111; --fg: #e1e3e5; --muted: #9ca3af;
    --card-bg: #1a1a1a; --card-shadow: 0 1px 3px rgba(0,0,0,0.3);
    --input-bg: #252525; --border: #333333;
  }
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font); background: var(--bg); color: var(--fg); min-height: 100vh; padding: 2rem 1rem; }
.wizard { max-width: 600px; margin: 0 auto; }
h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.subtitle { color: var(--muted); margin-bottom: 2rem; font-size: 0.9rem; }

/* Progress bar */
.progress { display: flex; gap: 0.5rem; margin-bottom: 2rem; }
.progress-step { flex: 1; height: 4px; border-radius: 2px; background: var(--border); transition: background 0.3s; }
.progress-step.done { background: var(--success); }
.progress-step.active { background: var(--accent); }

/* Card */
.card { background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; box-shadow: var(--card-shadow); }
.step { display: none; }
.step.active { display: block; }
.step-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem; }
.step-desc { color: var(--muted); font-size: 0.85rem; margin-bottom: 1.25rem; }

/* Forms */
label { display: block; font-weight: 500; font-size: 0.85rem; margin-bottom: 0.35rem; margin-top: 1rem; }
label:first-child { margin-top: 0; }
input[type="text"], input[type="password"], select {
  width: 100%; padding: 0.6rem 0.75rem; border: 1px solid var(--border);
  border-radius: 6px; background: var(--input-bg); color: var(--fg);
  font-size: 0.9rem; outline: none; transition: border-color 0.2s;
}
input:focus, select:focus { border-color: var(--accent); }
select { cursor: pointer; }

/* Buttons */
.btn { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.6rem 1.2rem; border: none; border-radius: 6px; font-size: 0.9rem; font-weight: 500; cursor: pointer; transition: all 0.2s; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: transparent; color: var(--accent); border: 1px solid var(--border); }
.btn-secondary:hover { background: var(--input-bg); }
.btn-success { background: var(--success); color: #fff; }
.btn-row { display: flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; }

/* Status messages */
.msg { padding: 0.6rem 0.75rem; border-radius: 6px; font-size: 0.85rem; margin-top: 0.75rem; display: none; }
.msg.ok { display: block; background: #e6f9f0; color: var(--success); border: 1px solid #b8e8d0; }
.msg.err { display: block; background: #fef0ee; color: var(--error); border: 1px solid #f5c6c0; }
@media (prefers-color-scheme: dark) {
  .msg.ok { background: #0a2e1f; border-color: #1a4a32; }
  .msg.err { background: #2e0a0a; border-color: #4a1a1a; }
}

/* Tabs */
.tabs { display: flex; gap: 0; margin-bottom: 1.25rem; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.tab-btn { flex: 1; padding: 0.5rem; text-align: center; font-size: 0.85rem; font-weight: 500; cursor: pointer; background: var(--input-bg); color: var(--muted); border: none; transition: all 0.2s; }
.tab-btn.active { background: var(--accent); color: #fff; }
.tab-content { display: none; }
.tab-content.active { display: block; }

/* Details/accordion */
details { margin-top: 0.75rem; border: 1px solid var(--border); border-radius: 6px; padding: 0.75rem; font-size: 0.82rem; color: var(--muted); }
details summary { cursor: pointer; font-weight: 500; color: var(--fg); }
details ol { margin: 0.5rem 0 0 1.25rem; line-height: 1.6; }

/* Device flow code display */
.device-code { font-family: "SF Mono", "Consolas", monospace; font-size: 1.8rem; font-weight: 700; letter-spacing: 0.15em; text-align: center; padding: 0.75rem; background: var(--input-bg); border-radius: 6px; margin: 0.75rem 0; user-select: all; }
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.6s linear infinite; margin-right: 0.4rem; vertical-align: middle; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Review table */
.review-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.review-table th, .review-table td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); }
.review-table th { color: var(--muted); font-weight: 500; }

/* Success banner */
.success-banner { text-align: center; padding: 2rem 1rem; }
.success-banner .check { font-size: 3rem; margin-bottom: 0.5rem; }
.success-banner p { color: var(--muted); margin-top: 0.5rem; font-size: 0.9rem; }
</style>
</head>
<body>
<div class="wizard">
  <h1>Theme Manager Setup</h1>
  <p class="subtitle">Connect your Shopify store and GitHub account.</p>

  <div class="progress">
    <div class="progress-step active" data-p="1"></div>
    <div class="progress-step" data-p="2"></div>
    <div class="progress-step" data-p="3"></div>
    <div class="progress-step" data-p="4"></div>
    <div class="progress-step" data-p="5"></div>
  </div>

  <!-- Step 1: Shopify -->
  <div class="card step active" data-step="1">
    <div class="step-title">Shopify Connection</div>
    <div class="step-desc">Connect to your Shopify store's Admin API.</div>

    <label for="shopify-domain">Store domain</label>
    <input type="text" id="shopify-domain" placeholder="your-store.myshopify.com">

    <label for="shopify-token">Admin API access token</label>
    <input type="password" id="shopify-token" placeholder="shpat_...">

    <details>
      <summary>How to get your access token</summary>
      <ol>
        <li>Go to your Shopify Admin</li>
        <li>Navigate to <strong>Settings &rarr; Apps and sales channels &rarr; Develop apps</strong></li>
        <li>Click <strong>Create an app</strong>, give it a name</li>
        <li>Under <strong>Configuration</strong>, click <strong>Configure Admin API scopes</strong></li>
        <li>Enable <strong>read_themes</strong> and <strong>write_themes</strong></li>
        <li>Click <strong>Install app</strong>, then <strong>Reveal token once</strong></li>
        <li>Copy the token and paste it above</li>
      </ol>
    </details>

    <div id="shopify-msg" class="msg"></div>
    <div class="btn-row">
      <span></span>
      <div style="display:flex;gap:0.5rem">
        <button class="btn btn-secondary" onclick="verifyShopify()">Verify</button>
        <button class="btn btn-primary" id="btn-next-1" disabled onclick="nextStep()">Next</button>
      </div>
    </div>
  </div>

  <!-- Step 2: GitHub -->
  <div class="card step" data-step="2">
    <div class="step-title">GitHub Connection</div>
    <div class="step-desc">Authenticate with GitHub to access your theme repositories.</div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('pat')">Personal Access Token</button>
      <button class="tab-btn" onclick="switchTab('device')">OAuth Device Flow</button>
    </div>

    <!-- PAT tab -->
    <div class="tab-content active" id="tab-pat">
      <label for="github-pat">Personal access token</label>
      <input type="password" id="github-pat" placeholder="ghp_... or github_pat_...">
      <details>
        <summary>How to create a token</summary>
        <ol>
          <li>Go to <strong>GitHub Settings &rarr; Developer settings &rarr; Personal access tokens &rarr; Fine-grained tokens</strong></li>
          <li>Click <strong>Generate new token</strong></li>
          <li>Select the repositories you want to grant access to (or all)</li>
          <li>Under <strong>Permissions &rarr; Repository permissions</strong>, enable <strong>Contents: Read and write</strong></li>
          <li>Click <strong>Generate token</strong> and paste it above</li>
        </ol>
      </details>
      <div style="margin-top:0.75rem">
        <button class="btn btn-secondary" onclick="verifyGithubPAT()">Verify</button>
      </div>
    </div>

    <!-- Device Flow tab -->
    <div class="tab-content" id="tab-device">
      <label for="github-client-id">GitHub OAuth App Client ID</label>
      <input type="text" id="github-client-id" placeholder="Ov23li...">
      <details>
        <summary>How to create an OAuth App</summary>
        <ol>
          <li>Go to <strong>GitHub Settings &rarr; Developer settings &rarr; OAuth Apps</strong></li>
          <li>Click <strong>New OAuth App</strong></li>
          <li>Set <strong>Homepage URL</strong> to <code>http://localhost:8420</code></li>
          <li>Set <strong>Authorization callback URL</strong> to <code>http://localhost:8420</code></li>
          <li>Click <strong>Register application</strong></li>
          <li>Copy the <strong>Client ID</strong> and paste it above</li>
        </ol>
      </details>
      <div style="margin-top:0.75rem">
        <button class="btn btn-secondary" id="btn-start-device" onclick="startDeviceFlow()">Start Authentication</button>
      </div>
      <div id="device-flow-area" style="display:none;margin-top:1rem">
        <p style="font-size:0.85rem;color:var(--muted)">Enter this code on GitHub:</p>
        <div class="device-code" id="device-user-code"></div>
        <p style="text-align:center">
          <a id="device-link" href="#" target="_blank" class="btn btn-primary" style="text-decoration:none">Open GitHub</a>
        </p>
        <p id="device-status" style="margin-top:0.75rem;font-size:0.85rem;color:var(--muted)">
          <span class="spinner"></span> Waiting for authorization...
        </p>
      </div>
    </div>

    <div id="github-msg" class="msg"></div>
    <div class="btn-row">
      <button class="btn btn-secondary" onclick="prevStep()">Back</button>
      <button class="btn btn-primary" id="btn-next-2" disabled onclick="nextStep()">Next</button>
    </div>
  </div>

  <!-- Step 3: Repo -->
  <div class="card step" data-step="3">
    <div class="step-title">Select Repository</div>
    <div class="step-desc">Choose the GitHub repo for this store. The agent will manage branches (main, staging, dev) within this single repo.</div>

    <label for="repo-owner">Repository owner</label>
    <select id="repo-owner" onchange="loadRepos()"></select>

    <div id="repos-loading" style="display:none;margin-top:1rem;font-size:0.85rem;color:var(--muted)">
      <span class="spinner"></span> Loading repositories...
    </div>

    <div id="repos-area" style="display:none">
      <label for="repo-select">Repository</label>
      <select id="repo-select"><option value="">Select a repository...</option></select>
    </div>

    <div id="repos-msg" class="msg"></div>
    <div class="btn-row">
      <button class="btn btn-secondary" onclick="prevStep()">Back</button>
      <button class="btn btn-primary" id="btn-next-3" onclick="nextStep()">Next</button>
    </div>
  </div>

  <!-- Step 4: Themes -->
  <div class="card step" data-step="4">
    <div class="step-title">Select Themes</div>
    <div class="step-desc">Map your Shopify themes to each environment.</div>

    <div id="themes-loading" style="font-size:0.85rem;color:var(--muted)">
      <span class="spinner"></span> Loading themes...
    </div>

    <div id="themes-area" style="display:none">
      <label for="theme-main">Production theme</label>
      <select id="theme-main"><option value="">Select a theme...</option></select>

      <label for="theme-staging">Staging theme</label>
      <select id="theme-staging"><option value="">Select a theme...</option></select>

      <label for="theme-dev">Development theme</label>
      <select id="theme-dev"><option value="">Select a theme...</option></select>
    </div>

    <div id="themes-msg" class="msg"></div>
    <div class="btn-row">
      <button class="btn btn-secondary" onclick="prevStep()">Back</button>
      <button class="btn btn-primary" id="btn-next-4" onclick="nextStep()">Next</button>
    </div>
  </div>

  <!-- Step 5: Review & Save -->
  <div class="card step" data-step="5">
    <div id="review-content">
      <div class="step-title">Review &amp; Save</div>
      <div class="step-desc">Confirm your configuration before saving.</div>
      <table class="review-table" id="review-table"></table>
      <div class="btn-row">
        <button class="btn btn-secondary" onclick="prevStep()">Back</button>
        <button class="btn btn-success" onclick="saveConfig()">Save Configuration</button>
      </div>
    </div>
    <div id="save-success" class="success-banner" style="display:none">
      <div class="check">&#10003;</div>
      <h2>Configuration Saved</h2>
      <p>Your <code>.env</code> file has been updated.</p>
      <p>You can close this tab. The server will shut down automatically.</p>
      <p style="margin-top:1rem;font-size:0.82rem">Run <code>python main.py --heartbeat</code> to start the agent.</p>
    </div>
  </div>
</div>

<script>
let current = 1;
const total = 5;
let devicePollTimer = null;
let reposCache = [];

function showStep(n) {
  document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
  document.querySelector(`[data-step="${n}"]`).classList.add('active');
  document.querySelectorAll('.progress-step').forEach(p => {
    const pn = +p.dataset.p;
    p.className = 'progress-step' + (pn < n ? ' done' : pn === n ? ' active' : '');
  });
}

function nextStep() {
  if (current < total) { current++; showStep(current); onStepEnter(current); }
}
function prevStep() {
  if (current > 1) { current--; showStep(current); }
}

async function onStepEnter(step) {
  if (step === 3) await loadOwnerAndRepos();
  if (step === 4) await loadThemes();
  if (step === 5) renderReview();
}

// -- Shopify ----------------------------------------------------------------
async function verifyShopify() {
  const domain = document.getElementById('shopify-domain').value;
  const token = document.getElementById('shopify-token').value;
  const msg = document.getElementById('shopify-msg');
  msg.className = 'msg'; msg.style.display = 'none';

  try {
    const r = await fetch('/api/shopify/verify', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({domain, token})
    });
    const d = await r.json();
    if (d.ok) {
      msg.className = 'msg ok'; msg.textContent = 'Connected to ' + d.shop_name;
      document.getElementById('btn-next-1').disabled = false;
    } else {
      msg.className = 'msg err'; msg.textContent = d.error;
    }
  } catch (e) { msg.className = 'msg err'; msg.textContent = e.message; }
}

// -- GitHub -----------------------------------------------------------------
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach((b, i) => b.classList.toggle('active', (tab === 'pat' ? i === 0 : i === 1)));
  document.getElementById('tab-pat').classList.toggle('active', tab === 'pat');
  document.getElementById('tab-device').classList.toggle('active', tab === 'device');
}

async function verifyGithubPAT() {
  const token = document.getElementById('github-pat').value;
  const msg = document.getElementById('github-msg');
  msg.className = 'msg'; msg.style.display = 'none';

  try {
    const r = await fetch('/api/github/verify-pat', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token})
    });
    const d = await r.json();
    if (d.ok) {
      msg.className = 'msg ok'; msg.textContent = 'Authenticated as ' + d.login + (d.name ? ' (' + d.name + ')' : '');
      document.getElementById('btn-next-2').disabled = false;
    } else {
      msg.className = 'msg err'; msg.textContent = d.error;
    }
  } catch (e) { msg.className = 'msg err'; msg.textContent = e.message; }
}

async function startDeviceFlow() {
  const clientId = document.getElementById('github-client-id').value;
  const msg = document.getElementById('github-msg');
  msg.className = 'msg'; msg.style.display = 'none';

  try {
    const r = await fetch('/api/github/device-flow/start', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({client_id: clientId})
    });
    const d = await r.json();
    if (!d.ok) { msg.className = 'msg err'; msg.textContent = d.error; return; }

    document.getElementById('device-flow-area').style.display = 'block';
    document.getElementById('device-user-code').textContent = d.user_code;
    document.getElementById('device-link').href = d.verification_uri;
    document.getElementById('device-status').innerHTML = '<span class="spinner"></span> Waiting for authorization...';
    document.getElementById('btn-start-device').disabled = true;

    const interval = (d.interval || 5) * 1000;
    if (devicePollTimer) clearInterval(devicePollTimer);
    devicePollTimer = setInterval(async () => {
      try {
        const pr = await fetch('/api/github/device-flow/poll', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({client_id: clientId, device_code: d.device_code})
        });
        const pd = await pr.json();
        if (pd.status === 'complete') {
          clearInterval(devicePollTimer);
          document.getElementById('device-status').innerHTML = '&#10003; Authenticated as ' + pd.login;
          document.getElementById('device-status').style.color = 'var(--success)';
          document.getElementById('btn-next-2').disabled = false;
          msg.className = 'msg ok'; msg.textContent = 'GitHub connected.';
        } else if (pd.status === 'error') {
          clearInterval(devicePollTimer);
          msg.className = 'msg err'; msg.textContent = pd.error;
          document.getElementById('btn-start-device').disabled = false;
        }
      } catch (e) { /* keep polling */ }
    }, interval);
  } catch (e) { msg.className = 'msg err'; msg.textContent = e.message; }
}

// -- Repos ------------------------------------------------------------------
async function loadOwnerAndRepos() {
  const sel = document.getElementById('repo-owner');
  try {
    const r = await fetch('/api/github/orgs');
    const d = await r.json();
    if (!d.ok) return;
    sel.innerHTML = '';
    if (d.user) sel.innerHTML += '<option value="' + d.user + '">' + d.user + ' (personal)</option>';
    (d.orgs || []).forEach(o => sel.innerHTML += '<option value="' + o + '">' + o + '</option>');
    await loadRepos();
  } catch (e) { console.error(e); }
}

async function loadRepos() {
  const owner = document.getElementById('repo-owner').value;
  document.getElementById('repos-loading').style.display = 'block';
  document.getElementById('repos-area').style.display = 'none';

  try {
    const r = await fetch('/api/github/repos?owner=' + encodeURIComponent(owner));
    const d = await r.json();
    if (!d.ok) return;
    reposCache = d.repos;
    const sel = document.getElementById('repo-select');
    sel.innerHTML = '<option value="">Select a repository...</option>';
    d.repos.forEach(repo => {
      const opt = document.createElement('option');
      opt.value = repo.name;
      opt.textContent = repo.name + (repo.description ? ' — ' + repo.description.slice(0, 50) : '');
      sel.appendChild(opt);
    });
    // Auto-select: match store slug from prefill domain
    const domainEl = document.getElementById('shopify-domain');
    if (domainEl && domainEl.value) {
      const slug = domainEl.value.replace('.myshopify.com', '').toLowerCase();
      const match = d.repos.find(repo => repo.name.toLowerCase() === slug);
      if (match) sel.value = match.name;
    }
    document.getElementById('repos-loading').style.display = 'none';
    document.getElementById('repos-area').style.display = 'block';
  } catch (e) { console.error(e); }
}

// -- Themes -----------------------------------------------------------------
async function loadThemes() {
  document.getElementById('themes-loading').style.display = 'block';
  document.getElementById('themes-area').style.display = 'none';

  try {
    const r = await fetch('/api/shopify/themes');
    const d = await r.json();
    if (!d.ok) { document.getElementById('themes-msg').className = 'msg err'; document.getElementById('themes-msg').textContent = d.error; return; }

    ['main', 'staging', 'dev'].forEach(env => {
      const sel = document.getElementById('theme-' + env);
      sel.innerHTML = '<option value="">Select a theme...</option>';
      d.themes.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.id;
        opt.textContent = t.name + ' (ID: ' + t.id + ') [' + t.role + ']';
        sel.appendChild(opt);
      });
      // Auto-select
      const match = d.themes.find(t => {
        if (env === 'main') return t.role === 'main';
        const n = t.name.toLowerCase();
        if (env === 'staging') return n.includes('stag');
        return n.includes('dev');
      });
      if (match) sel.value = match.id;
    });
    document.getElementById('themes-loading').style.display = 'none';
    document.getElementById('themes-area').style.display = 'block';
  } catch (e) { console.error(e); }
}

// -- Review & Save ----------------------------------------------------------
function renderReview() {
  const owner = document.getElementById('repo-owner').value;
  const repo = document.getElementById('repo-select').value;
  const rows = [
    ['Shopify Store', document.getElementById('shopify-domain').value],
    ['GitHub Repo', owner + '/' + repo],
    ['Branches', 'main, staging, dev (created automatically)'],
  ];
  const envs = ['main', 'staging', 'dev'];
  const labels = ['Production Theme', 'Staging Theme', 'Development Theme'];
  envs.forEach((env, i) => {
    const themeSel = document.getElementById('theme-' + env);
    const themeName = themeSel.options[themeSel.selectedIndex]?.textContent || '(not set)';
    const themeId = themeSel.value || '—';
    rows.push([labels[i], themeName + (themeId !== '—' ? ' (ID: ' + themeId + ')' : '')]);
  });

  const table = document.getElementById('review-table');
  table.innerHTML = rows.map(([k, v]) => '<tr><th>' + k + '</th><td>' + v + '</td></tr>').join('');
}

async function saveConfig() {
  const owner = document.getElementById('repo-owner').value;
  try {
    const r = await fetch('/api/save', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        github_owner: owner,
        repo: document.getElementById('repo-select').value,
        themes: {
          main: document.getElementById('theme-main').value,
          staging: document.getElementById('theme-staging').value,
          dev: document.getElementById('theme-dev').value,
        }
      })
    });
    const d = await r.json();
    if (d.ok) {
      document.getElementById('review-content').style.display = 'none';
      document.getElementById('save-success').style.display = 'block';
      document.querySelectorAll('.progress-step').forEach(p => p.className = 'progress-step done');
    }
  } catch (e) { console.error(e); }
}

// Auto-prefill store domain when launched for a specific store
fetch('/api/prefill').then(r => r.json()).then(d => {
  if (d.domain) {
    const el = document.getElementById('shopify-domain');
    if (el && !el.value) el.value = d.domain;
  }
}).catch(() => {});
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# App assembly
# ---------------------------------------------------------------------------

app = Starlette(
    routes=[
        Route("/", homepage),
        Route("/api/shopify/verify", shopify_verify, methods=["POST"]),
        Route("/api/github/verify-pat", github_verify_pat, methods=["POST"]),
        Route("/api/github/device-flow/start", github_device_flow_start, methods=["POST"]),
        Route("/api/github/device-flow/poll", github_device_flow_poll, methods=["POST"]),
        Route("/api/github/orgs", github_orgs),
        Route("/api/github/repos", github_repos),
        Route("/api/shopify/themes", shopify_themes),
        Route("/api/prefill", get_prefill),
        Route("/api/save", save_config, methods=["POST"]),
    ],
)


def run_setup_wizard(
    target_dir: Path | None = None,
    prefill_domain: str = "",
) -> None:
    """Start the setup wizard server and open the browser.

    Args:
        target_dir: Project directory to write .env to. Defaults to theme-manager/.
        prefill_domain: Store domain to pre-populate in the wizard.
    """
    global ENV_PATH, _prefill_domain

    if target_dir is not None:
        target_dir.mkdir(parents=True, exist_ok=True)
        ENV_PATH = target_dir / ".env"

    _prefill_domain = prefill_domain

    port = PORT
    label = f" for {prefill_domain}" if prefill_domain else ""
    print(f"\n  Theme Manager Setup Wizard{label}")
    print(f"  Saving to: {ENV_PATH}")
    print(f"  Open http://localhost:{port} in your browser\n")
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
