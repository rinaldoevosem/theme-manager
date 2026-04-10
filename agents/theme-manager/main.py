"""Shopify Theme Manager — main entry point.

Run standalone:
    python main.py "Check the sync status of all environments"

Run via Paperclip heartbeat:
    python main.py --heartbeat
"""

import argparse
import asyncio
import json
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
from config import Config, config, store_slug_from_domain
from system_prompt import SYSTEM_PROMPT
from tools import theme_tools_server

PROJECTS_ROOT = Path(__file__).resolve().parent.parent.parent  # /Users/melo/shopify-theme/

_DOMAIN_RE = re.compile(r"[\w][\w-]*\.myshopify\.com")


def extract_store_domain(task: dict) -> str | None:
    """Extract a *.myshopify.com domain from a Paperclip task."""
    # Check structured metadata first
    metadata = task.get("metadata") or {}
    if domain := metadata.get("store_domain"):
        return domain.strip().lower()

    # Regex-scan title + description
    text = f"{task.get('title', '')} {task.get('description', '')}"
    match = _DOMAIN_RE.search(text)
    return match.group(0).lower() if match else None


def resolve_project_dir(store_domain: str) -> Path:
    """Return the project directory for a store (e.g., /Users/melo/shopify-theme/horizon-clone/)."""
    slug = store_slug_from_domain(store_domain)
    return PROJECTS_ROOT / slug


def build_options() -> ClaudeAgentOptions:
    """Build the agent options with tools, subagents, and permissions."""
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        permission_mode="default",
        allowed_tools=[
            "Bash",
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "WebFetch",
            "Agent",
            "mcp__theme-tools__get_theme_status",
            "mcp__theme-tools__check_promotion_readiness",
            "mcp__theme-tools__generate_change_summary",
        ],
        mcp_servers={"theme-tools": theme_tools_server},
        agents=subagents,
        env={
            "GITHUB_TOKEN": config.github_token,
            "SHOPIFY_FLAG_STORE": config.shopify_store_domain,
            "SHOPIFY_ACCESS_TOKEN": config.shopify_access_token,
        },
    )


async def run_prompt(prompt: str) -> str | None:
    """Run a single prompt through the theme manager agent and return the result."""
    options = build_options()
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
    envs = config.environments
    repo_list = ", ".join(
        f"{config.github_owner}/{env.github_repo}" for env in envs.values()
    )
    return (
        f"Perform a routine health check for GitHub owner '{config.github_owner}':\n"
        "1. Use get_theme_status to review all three environments.\n"
        f"2. Run `gh pr list` for each of these repos: {repo_list}.\n"
        "3. If any PRs are open, use the pr-reviewer subagent to review them.\n"
        "4. If any environment appears out of sync, use the sync-checker subagent "
        "to investigate.\n"
        "5. Summarize findings in a concise status update."
    )


def _build_task_prompt(task: dict) -> str:
    """Convert a Paperclip task into an agent prompt."""
    title = task.get("title", "Untitled task")
    description = task.get("description", "")
    return (
        f"You have been assigned the following task:\n\n"
        f"**{title}**\n\n"
        f"{description}\n\n"
        "Use the available tools and subagents to complete this task. "
        "Provide a clear summary of what you did and the outcome."
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


async def heartbeat() -> None:
    """Paperclip heartbeat mode.

    When Paperclip credentials are configured, integrates with the Paperclip
    task lifecycle (fetch tasks, checkout, update status, post comments).
    Falls back to a standalone health check when Paperclip is not configured.
    """
    print("[heartbeat] Theme Manager waking up...", flush=True)

    # Check if Paperclip API is configured
    if config.paperclip_company_id:
        from paperclip_client import PaperclipClient

        client = PaperclipClient(
            api_url=config.paperclip_api_url,
            api_key=config.paperclip_api_key,
            company_id=config.paperclip_company_id,
            agent_id=config.paperclip_agent_id,
        )
        try:
            await _heartbeat_with_paperclip(client)
        finally:
            await client.close()
    else:
        print("[heartbeat] No Paperclip credentials — running standalone health check", flush=True)
        result = await run_prompt(_health_check_prompt())
        _write_heartbeat_output(result)


async def _heartbeat_with_paperclip(client) -> None:
    """Run heartbeat with full Paperclip task lifecycle integration."""
    from paperclip_client import PaperclipClient

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
                    print(f"[heartbeat] Missing credentials for {store_domain} — launching setup wizard", flush=True)
                    await client.post_comment(
                        task_id,
                        f"Opening setup wizard for **{store_domain}**. "
                        "Waiting for user to complete authentication..."
                    )

                    # Blocking — wizard runs until user saves or closes
                    from setup_server import run_setup_wizard
                    run_setup_wizard(target_dir=project_dir, prefill_domain=store_domain)

                    # Reload config after wizard completes
                    store_config = Config.load(project_dir)
                    if not store_config.has_valid_credentials():
                        msg = f"Setup wizard closed without valid credentials for {store_domain}."
                        print(f"[heartbeat] {msg}", flush=True)
                        await client.post_comment(task_id, msg)
                        await client.update_task_status(task_id, "blocked")
                        continue

                    print(f"[heartbeat] Credentials configured for {store_domain}", flush=True)

                # Swap global config so tools/agents use the store-specific config
                config_module.config = store_config

            try:
                result = await run_prompt(_build_task_prompt(task))
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
        result = await run_prompt(_health_check_prompt())

    _write_heartbeat_output(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Shopify Theme Manager Agent")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the agent")
    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Run in Paperclip heartbeat mode (automated health check)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Launch the browser-based setup wizard",
    )
    parser.add_argument(
        "--store-domain",
        help="Store domain for setup (e.g., horizon-clone.myshopify.com)",
    )
    args = parser.parse_args()

    if args.setup:
        from setup_server import run_setup_wizard
        target_dir = None
        prefill_domain = args.store_domain or ""
        if prefill_domain:
            target_dir = resolve_project_dir(prefill_domain)
            target_dir.mkdir(parents=True, exist_ok=True)
        run_setup_wizard(target_dir=target_dir, prefill_domain=prefill_domain)
    elif args.heartbeat:
        asyncio.run(heartbeat())
    elif args.prompt:
        asyncio.run(run_prompt(args.prompt))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
