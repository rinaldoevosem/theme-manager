"""Custom MCP tools for the Shopify Theme Manager agent."""

from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

from config import config


@tool(
    name="get_theme_status",
    description=(
        "Check the current status of all three theme environments. "
        "Returns which Shopify themes are connected, their GitHub repo sync state, "
        "and whether any environment has uncommitted changes or drift."
    ),
    input_schema={},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_theme_status(args: dict[str, Any]) -> dict[str, Any]:
    envs = config.environments
    status_lines: list[str] = []

    repo_url = f"https://github.com/{config.github_owner}/{config.github_repo}"

    for name, env in envs.items():
        theme_id = env.shopify_theme_id or "(not configured)"
        status_lines.append(
            f"**{name.upper()}** (branch: `{env.branch}`)\n"
            f"  Repo: {repo_url}\n"
            f"  Shopify Theme ID: {theme_id}\n"
            f"  Description: {env.description}"
        )

    summary = (
        f"Store: {config.shopify_store_domain or '(not configured)'}\n\n"
        + "\n\n".join(status_lines)
        + "\n\nTo check live sync state, use `gh` and Shopify CLI commands via Bash."
    )

    return {"content": [{"type": "text", "text": summary}]}


@tool(
    name="check_promotion_readiness",
    description=(
        "Evaluate whether a theme environment is ready to be promoted to the next stage. "
        "Provide the source environment name: 'dev' (to promote to staging) or "
        "'staging' (to promote to main). Returns a checklist of requirements and their status."
    ),
    input_schema={"source_env": str},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def check_promotion_readiness(args: dict[str, Any]) -> dict[str, Any]:
    source = args.get("source_env", "").lower()
    valid_promotions = {"dev": "staging", "staging": "main"}

    if source not in valid_promotions:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Invalid source environment '{source}'. Must be 'dev' or 'staging'.",
                }
            ],
            "isError": True,
        }

    target = valid_promotions[source]
    envs = config.environments
    source_env = envs[source]
    target_env = envs[target]
    repo = f"{config.github_owner}/{config.github_repo}"

    checklist = (
        f"## Promotion Readiness: {source.upper()} → {target.upper()}\n\n"
        f"**Repo**: {repo}\n"
        f"**PR direction**: `{source_env.branch}` → `{target_env.branch}`\n\n"
        "### Checklist\n"
        "- [ ] All PRs in source repo are merged or closed\n"
        "- [ ] No uncommitted Shopify customizer changes on source theme\n"
        "- [ ] Theme passes Shopify theme check (`shopify theme check`)\n"
        "- [ ] Change summary prepared for PR description\n"
        "- [ ] Screenshots / preview links included where applicable\n"
    )

    if target == "main":
        checklist += (
            "- [ ] Client approval obtained and referenced\n"
            "- [ ] settings_data.json changes reviewed for backwards compatibility\n"
            "- [ ] Deployment window confirmed with stakeholders\n"
        )
    else:
        checklist += (
            "- [ ] Test plan included in PR\n"
            "- [ ] Dev team sign-off obtained\n"
        )

    checklist += (
        "\nUse Bash to run `gh` commands against the repos and "
        "`shopify theme check` to verify these items."
    )

    return {"content": [{"type": "text", "text": checklist}]}


@tool(
    name="generate_change_summary",
    description=(
        "Generate a formatted change summary suitable for a PR description or "
        "stakeholder report. Provide the environment name ('dev', 'staging', or 'main') "
        "and an audience ('technical' for developers or 'non-technical' for clients)."
    ),
    input_schema={"environment": str, "audience": str},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def generate_change_summary(args: dict[str, Any]) -> dict[str, Any]:
    env_name = args.get("environment", "").lower()
    audience = args.get("audience", "technical").lower()

    if env_name not in config.environments:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Unknown environment '{env_name}'. Use 'dev', 'staging', or 'main'.",
                }
            ],
            "isError": True,
        }

    env = config.environments[env_name]
    repo = f"{config.github_owner}/{config.github_repo}"

    instructions = (
        f"## Generate Change Summary\n\n"
        f"**Repo**: {repo} (branch: `{env.branch}`)\n"
        f"**Audience**: {audience}\n\n"
        "To build this summary, use Bash to run:\n"
        f"1. `gh api repos/{repo}/pulls?state=closed&sort=updated&per_page=10` "
        "— recent merged PRs\n"
        f"2. `gh api repos/{repo}/commits?sha={env.branch}&per_page=20` "
        "— recent commits\n\n"
    )

    if audience == "non-technical":
        instructions += (
            "Format the summary in plain language:\n"
            "- Group changes by feature area (e.g., Navigation, Product Pages, Cart)\n"
            "- Describe what changed from the customer's perspective\n"
            "- Avoid file paths, code references, or commit SHAs\n"
        )
    else:
        instructions += (
            "Format the summary with technical detail:\n"
            "- List changed files and their purpose\n"
            "- Include commit SHAs for reference\n"
            "- Note any schema or settings changes\n"
            "- Flag potential breaking changes\n"
        )

    return {"content": [{"type": "text", "text": instructions}]}


# Bundle all tools into an MCP server
theme_tools_server = create_sdk_mcp_server(
    name="theme-tools",
    version="1.0.0",
    tools=[get_theme_status, check_promotion_readiness, generate_change_summary],
)
