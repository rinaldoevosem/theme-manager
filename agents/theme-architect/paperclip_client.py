"""Paperclip API client for the Theme Architect agent.

Handles communication with the Paperclip server during heartbeats:
task checkout, status updates, comments, and cost reporting.
"""

from __future__ import annotations

from typing import Any

import httpx


class PaperclipClient:
    """Async HTTP client for the Paperclip REST API."""

    def __init__(self, api_url: str, api_key: str, company_id: str, agent_id: str):
        self.base_url = api_url.rstrip("/")
        self.company_url = f"{self.base_url}/api/companies/{company_id}"
        self.agent_id = agent_id
        self.headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(headers=self.headers, timeout=30)

    async def close(self) -> None:
        await self._client.aclose()

    # -- Tasks ---------------------------------------------------------------

    async def fetch_assigned_tasks(self) -> list[dict[str, Any]]:
        """Fetch tasks assigned to this agent."""
        resp = await self._client.get(
            f"{self.company_url}/issues",
            params={"assigneeAgentId": self.agent_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def checkout_task(self, task_id: str) -> dict[str, Any]:
        """Optional task lock. Best-effort — silently skips if endpoint rejects."""
        try:
            resp = await self._client.post(
                f"{self.base_url}/api/issues/{task_id}/checkout",
                json={"agentId": self.agent_id, "expectedStatuses": ["todo", "backlog", "in_progress"]},
            )
            if resp.status_code < 400:
                return resp.json()
        except Exception:
            pass
        return {}

    async def update_task_status(self, task_id: str, status: str) -> dict[str, Any]:
        """Update task status: backlog, todo, in_progress, in_review, blocked, done, cancelled."""
        resp = await self._client.patch(
            f"{self.base_url}/api/issues/{task_id}",
            json={"status": status},
        )
        resp.raise_for_status()
        return resp.json()

    async def post_comment(self, task_id: str, content: str) -> dict[str, Any]:
        """Post a comment/result on a task."""
        resp = await self._client.post(
            f"{self.base_url}/api/issues/{task_id}/comments",
            json={"body": content},
        )
        resp.raise_for_status()
        return resp.json()

    # -- Cost tracking -------------------------------------------------------

    async def report_cost(
        self,
        cost_usd: float,
        *,
        issue_id: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> dict[str, Any]:
        """Report a cost event to Paperclip for budget tracking."""
        resp = await self._client.post(
            f"{self.company_url}/cost-events",
            json={
                "agentId": self.agent_id,
                "issueId": issue_id,
                "provider": "anthropic",
                "model": "claude",
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "costCents": int(cost_usd * 100),
            },
        )
        resp.raise_for_status()
        return resp.json()

    # -- Heartbeat runs ------------------------------------------------------

    async def complete_run(self, run_id: str) -> dict[str, Any]:
        """Notify Paperclip that a heartbeat run has completed."""
        resp = await self._client.post(
            f"{self.base_url}/api/heartbeat-runs/{run_id}/complete"
        )
        resp.raise_for_status()
        return resp.json()
