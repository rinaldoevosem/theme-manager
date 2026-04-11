"""Shopify Theme Designer — main entry point.

Run standalone:
    python main.py "Apply the design tokens from this Figma file: <url>"

Run via Paperclip heartbeat:
    python main.py --heartbeat

Dry-run (preview changes without writing):
    python main.py --dry-run "Apply design tokens from <url>"
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

from claude_agent_sdk import (
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    query,
)

import config as config_module
from agents import subagents
from config import Config, config, store_slug_from_domain, PROJECTS_ROOT
from system_prompt import SYSTEM_PROMPT
from tools import designer_tools_server

_DOMAIN_RE = re.compile(r"[\w][\w-]*\.myshopify\.com")
_FIGMA_RE = re.compile(r"https?://(?:www\.)?figma\.com/[\w/\-?=&]+")


def extract_store_domain(task: dict) -> str | None:
    """Extract a *.myshopify.com domain from a Paperclip task."""
    metadata = task.get("metadata") or {}
    if domain := metadata.get("store_domain"):
        return domain.strip().lower()

    text = f"{task.get('title', '')} {task.get('description', '')}"
    match = _DOMAIN_RE.search(text)
    return match.group(0).lower() if match else None


def extract_figma_url(task: dict) -> str | None:
    """Extract a Figma URL from a Paperclip task."""
    metadata = task.get("metadata") or {}
    if url := metadata.get("figma_url"):
        return url.strip()

    text = f"{task.get('title', '')} {task.get('description', '')}"
    match = _FIGMA_RE.search(text)
    return match.group(0) if match else None


def resolve_project_dir(store_domain: str) -> Path:
    """Return the project directory for a store."""
    slug = store_slug_from_domain(store_domain)
    return PROJECTS_ROOT / slug


def build_options(model: str | None = None, dry_run: bool = False) -> ClaudeAgentOptions:
    """Build the agent options — includes write permissions for settings updates.

    Args:
        model: Optional model override (e.g. 'claude-opus-4-6', 'claude-sonnet-4-6').
        dry_run: If True, removes write tools from allowed list.
    """
    allowed_tools = [
        # Filesystem tools
        "Read",
        "Glob",
        "Grep",
        # Subagent invocation
        "Agent",
        # Custom designer tools
        "mcp__designer-tools__parse_settings_schema",
        "mcp__designer-tools__get_shopify_fonts",
        "mcp__designer-tools__validate_setting_value",
        # Figma tools (available at platform level)
        "mcp__plugin_figma_figma__get_design_context",
        "mcp__plugin_figma_figma__get_screenshot",
        "mcp__plugin_figma_figma__get_metadata",
    ]

    if not dry_run:
        allowed_tools.append("mcp__designer-tools__apply_design_tokens")

    mcp_servers: dict = {"designer-tools": designer_tools_server}

    # Add shopify-dev MCP if configured
    if config.shopify_dev_mcp_path and Path(config.shopify_dev_mcp_path).exists():
        try:
            from claude_agent_sdk import McpServerConfig
            mcp_servers["shopify-dev"] = McpServerConfig(
                command="node",
                args=[config.shopify_dev_mcp_path],
            )
            allowed_tools.append("mcp__shopify-dev__search_docs")
        except ImportError:
            pass

    opts: dict = {
        "system_prompt": SYSTEM_PROMPT,
        "permission_mode": "default",
        "allowed_tools": allowed_tools,
        "mcp_servers": mcp_servers,
        "agents": subagents,
        "env": {"GITHUB_TOKEN": config.github_token},
    }
    if model:
        opts["model"] = model

    return ClaudeAgentOptions(**opts)


async def run_prompt(prompt: str, model: str | None = None, dry_run: bool = False) -> str | None:
    """Run a single prompt through the theme designer agent and return the result."""
    options = build_options(model=model, dry_run=dry_run)
    result_text: str | None = None

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, flush=True)
        elif isinstance(message, ResultMessage):
            result_text = message.result
            if message.is_error:
                print(f"\n[Error] {message.subtype}: {message.result}", file=sys.stderr)
            else:
                print(f"\n[Done] Cost: ${message.total_cost_usd or 0:.4f} | "
                      f"Turns: {message.num_turns} | "
                      f"Duration: {message.duration_ms / 1000:.1f}s")

    return result_text


def _health_check_prompt() -> str:
    """Build the default health-check prompt when no tasks are assigned."""
    theme_dir = config.theme_repo_dir
    if not theme_dir or not theme_dir.is_dir():
        return (
            "No theme repository found. Report that the theme-designer agent "
            "needs a valid store configuration with a pulled theme repo at "
            f"{theme_dir or '(not configured)'}."
        )

    schema_path = theme_dir / "config" / "settings_schema.json"
    data_path = theme_dir / "config" / "settings_data.json"

    if not schema_path.exists() or not data_path.exists():
        return (
            f"Theme repo found at {theme_dir} but settings files are missing. "
            f"Schema exists: {schema_path.exists()}, Data exists: {data_path.exists()}. "
            "The theme may need to be pulled from Shopify first."
        )

    return (
        f"Perform a theme settings health check:\n"
        f"1. Use parse_settings_schema on '{theme_dir}' to survey all settings.\n"
        "2. Report a summary: total configurable settings, number of color schemes, "
        "fonts currently in use.\n"
        "3. Flag any settings that are still at their default values vs. customized.\n"
        "4. Summarize the current typography setup (fonts, heading sizes).\n"
        "5. Summarize the primary color scheme (scheme-1)."
    )


def _build_task_prompt(task: dict, dry_run: bool = False) -> str:
    """Convert a Paperclip task into an agent prompt."""
    title = task.get("title", "Untitled task")
    description = task.get("description", "")

    # Include theme_dir context if available
    theme_dir = config.theme_repo_dir
    context = ""
    if theme_dir and theme_dir.is_dir():
        context = f"\n\nTheme directory: {theme_dir}\n"

    # Extract Figma URL if present
    figma_url = extract_figma_url(task)
    figma_context = ""
    if figma_url:
        figma_context = f"\nFigma design URL: {figma_url}\n"

    dry_run_note = ""
    if dry_run:
        dry_run_note = (
            "\n\n**DRY RUN MODE**: Do NOT use apply_design_tokens. Instead, "
            "use parse_settings_schema and validate_setting_value to preview "
            "what changes would be made, and present the proposed changes "
            "without writing them."
        )

    return (
        f"You have been assigned the following task:\n\n"
        f"**{title}**\n\n"
        f"{description}{context}{figma_context}{dry_run_note}\n"
        "Use the available tools and subagents to complete this task. "
        "Follow the workflow: interpret the design → parse the schema → "
        "map tokens to settings → apply changes → report results."
    )


def _write_heartbeat_output(result: str | None) -> None:
    """Write heartbeat result to a local JSON file (backwards compat)."""
    output_path = Path(__file__).parent / "heartbeat_output.json"
    output_path.write_text(
        json.dumps(
            {
                "agent": config.paperclip_agent_id,
                "status": "completed",
                "result": result,
            },
            indent=2,
        )
    )
    print(f"[heartbeat] Output written to {output_path}", flush=True)


async def heartbeat(model: str | None = None) -> None:
    """Paperclip heartbeat mode."""
    print(f"[heartbeat] Theme Designer waking up... (model={model or 'default'})", flush=True)

    if config.paperclip_company_id:
        from paperclip_client import PaperclipClient

        client = PaperclipClient(
            api_url=config.paperclip_api_url,
            api_key=config.paperclip_api_key,
            company_id=config.paperclip_company_id,
            agent_id=config.paperclip_agent_id,
        )
        try:
            await _heartbeat_with_paperclip(client, model=model)
        finally:
            await client.close()
    else:
        print("[heartbeat] No Paperclip credentials — running standalone health check", flush=True)
        result = await run_prompt(_health_check_prompt(), model=model)
        _write_heartbeat_output(result)


async def _heartbeat_with_paperclip(client, model: str | None = None) -> None:
    """Run heartbeat with full Paperclip task lifecycle integration."""
    all_tasks = await client.fetch_assigned_tasks()
    tasks = [t for t in all_tasks if t.get("status") == "todo"]
    result: str | None = None

    if tasks:
        print(f"[heartbeat] Found {len(tasks)} todo task(s) (of {len(all_tasks)} assigned)", flush=True)
        for task in tasks:
            task_id = task["id"]
            title = task.get("title", "Untitled")
            print(f"[heartbeat] Processing: {title}", flush=True)

            await client.checkout_task(task_id)
            await client.update_task_status(task_id, "in_progress")

            # Detect store domain and resolve per-store project directory
            store_domain = extract_store_domain(task)
            store_config: Config | None = None

            if store_domain:
                project_dir = resolve_project_dir(store_domain)
                project_dir.mkdir(parents=True, exist_ok=True)
                print(f"[heartbeat] Store: {store_domain} → {project_dir}", flush=True)

                store_config = Config.load(project_dir)

                if not store_config.has_valid_credentials():
                    msg = (
                        f"Missing credentials for {store_domain}. "
                        "Please run the theme-manager setup wizard first: "
                        f"`cd ../theme-manager && python main.py --setup --store-domain {store_domain}`"
                    )
                    print(f"[heartbeat] {msg}", flush=True)
                    await client.post_comment(task_id, msg)
                    await client.update_task_status(task_id, "blocked")
                    continue

                # Swap global config so tools use the store-specific config
                config_module.config = store_config

            try:
                result = await run_prompt(_build_task_prompt(task), model=model)
                await client.post_comment(task_id, result or "Task completed — no output.")
                await client.update_task_status(task_id, "done")
                print(f"[heartbeat] Completed: {title}", flush=True)
            except Exception as exc:
                error_msg = f"Task failed: {exc}"
                print(f"[heartbeat] {error_msg}", file=sys.stderr, flush=True)
                await client.post_comment(task_id, error_msg)
                await client.update_task_status(task_id, "blocked")
    else:
        print("[heartbeat] No assigned tasks — running health check", flush=True)
        result = await run_prompt(_health_check_prompt(), model=model)

    _write_heartbeat_output(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Shopify Theme Designer Agent")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the agent")
    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Run in Paperclip heartbeat mode (automated task processing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to settings_data.json",
    )
    parser.add_argument(
        "--model",
        help="Override the model (e.g. claude-opus-4-6, claude-sonnet-4-6). "
             "Can also be set via THEME_DESIGNER_MODEL env var. "
             "Defaults to the Claude CLI default (Sonnet).",
    )
    args = parser.parse_args()

    # Model precedence: --model flag > env var > None (SDK default)
    model = args.model or os.getenv("THEME_DESIGNER_MODEL") or None

    if args.heartbeat:
        asyncio.run(heartbeat(model=model))
    elif args.prompt:
        asyncio.run(run_prompt(args.prompt, model=model, dry_run=args.dry_run))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
