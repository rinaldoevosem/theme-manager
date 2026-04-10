"""Shopify Theme Architect — main entry point.

Run standalone:
    python main.py "Which section best fits a hero banner with video background?"

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
from config import Config, config, store_slug_from_domain, PROJECTS_ROOT
from system_prompt import SYSTEM_PROMPT
from tools import architect_tools_server

_DOMAIN_RE = re.compile(r"[\w][\w-]*\.myshopify\.com")


def extract_store_domain(task: dict) -> str | None:
    """Extract a *.myshopify.com domain from a Paperclip task."""
    metadata = task.get("metadata") or {}
    if domain := metadata.get("store_domain"):
        return domain.strip().lower()

    text = f"{task.get('title', '')} {task.get('description', '')}"
    match = _DOMAIN_RE.search(text)
    return match.group(0).lower() if match else None


def resolve_project_dir(store_domain: str) -> Path:
    """Return the project directory for a store."""
    slug = store_slug_from_domain(store_domain)
    return PROJECTS_ROOT / slug


def build_options() -> ClaudeAgentOptions:
    """Build the agent options — read-only tools only."""
    allowed_tools = [
        # Read-only filesystem tools
        "Read",
        "Glob",
        "Grep",
        # Subagent invocation
        "Agent",
        # Custom architect tools
        "mcp__architect-tools__analyze_theme_architecture",
        "mcp__architect-tools__get_section_details",
        "mcp__architect-tools__match_section_to_design",
        # Figma tools (available at platform level)
        "mcp__plugin_figma_figma__get_design_context",
        "mcp__plugin_figma_figma__get_screenshot",
        "mcp__plugin_figma_figma__get_metadata",
    ]

    mcp_servers: dict = {"architect-tools": architect_tools_server}

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
            # McpServerConfig not available in this SDK version — skip
            pass

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        permission_mode="default",
        allowed_tools=allowed_tools,
        mcp_servers=mcp_servers,
        agents=subagents,
        env={
            "GITHUB_TOKEN": config.github_token,
        },
    )


async def run_prompt(prompt: str) -> str | None:
    """Run a single prompt through the theme architect agent and return the result."""
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
    theme_dir = config.theme_repo_dir
    if not theme_dir or not theme_dir.is_dir():
        return (
            "No theme repository found. Report that the theme-architect agent "
            "needs a valid store configuration with a pulled theme repo at "
            f"{theme_dir or '(not configured)'}."
        )

    return (
        f"Perform a theme architecture health check:\n"
        f"1. Use analyze_theme_architecture on '{theme_dir}' to survey all sections.\n"
        "2. Report a summary: total sections, total blocks, total snippets.\n"
        "3. Flag any sections that have no presets (may be orphaned or header/footer only).\n"
        "4. Flag any sections with 0 block types (static sections).\n"
        "5. Summarize the theme's overall architecture and section coverage."
    )


def _build_task_prompt(task: dict) -> str:
    """Convert a Paperclip task into an agent prompt."""
    title = task.get("title", "Untitled task")
    description = task.get("description", "")

    # Include theme_dir context if available
    theme_dir = config.theme_repo_dir
    context = ""
    if theme_dir and theme_dir.is_dir():
        context = f"\n\nTheme directory: {theme_dir}\n"

    return (
        f"You have been assigned the following task:\n\n"
        f"**{title}**\n\n"
        f"{description}{context}\n"
        "Use the available tools and subagents to complete this task. "
        "Remember: you are read-only — analyze and recommend, never modify files."
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
    """Paperclip heartbeat mode."""
    print("[heartbeat] Theme Architect waking up...", flush=True)

    if config.paperclip_api_key and config.paperclip_company_id:
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
    tasks = await client.fetch_assigned_tasks()
    result: str | None = None

    if tasks:
        print(f"[heartbeat] Found {len(tasks)} assigned task(s)", flush=True)
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
    parser = argparse.ArgumentParser(description="Shopify Theme Architect Agent")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the agent")
    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Run in Paperclip heartbeat mode (automated health check)",
    )
    args = parser.parse_args()

    if args.heartbeat:
        asyncio.run(heartbeat())
    elif args.prompt:
        asyncio.run(run_prompt(args.prompt))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
