"""Async Paperclip API client for the eval runner."""

from __future__ import annotations

from typing import Any

import httpx


class PaperclipClient:
    """Async HTTP client for Paperclip REST API.

    Server runs unauthenticated, so no API key is needed.
    """

    def __init__(self, api_url: str, company_id: str):
        self.base_url = api_url.rstrip("/")
        self.company_id = company_id
        self.company_url = f"{self.base_url}/api/companies/{company_id}"
        self._client = httpx.AsyncClient(
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

    async def close(self) -> None:
        await self._client.aclose()

    # -- Issues / Tasks ------------------------------------------------------

    async def create_issue(
        self,
        title: str,
        description: str,
        assignee_agent_id: str,
        metadata: dict[str, Any] | None = None,
        priority: str = "medium",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "assigneeAgentId": assignee_agent_id,
            "priority": priority,
            "status": "todo",
        }
        if metadata:
            payload["metadata"] = metadata

        resp = await self._client.post(f"{self.company_url}/issues", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def list_issues(
        self,
        assignee_agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if assignee_agent_id:
            params["assigneeAgentId"] = assignee_agent_id

        resp = await self._client.get(f"{self.company_url}/issues", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Fetch a single issue by ID by listing and filtering."""
        issues = await self.list_issues()
        for issue in issues:
            if issue.get("id") == issue_id:
                return issue
        return None

    async def get_comments(self, issue_id: str) -> list[dict[str, Any]]:
        resp = await self._client.get(f"{self.base_url}/api/issues/{issue_id}/comments")
        resp.raise_for_status()
        data = resp.json()
        # API may return {comments: [...]} or just [...]
        if isinstance(data, dict) and "comments" in data:
            return data["comments"]
        return data if isinstance(data, list) else []

    async def delete_issue(self, issue_id: str) -> bool:
        try:
            resp = await self._client.delete(f"{self.base_url}/api/issues/{issue_id}")
            return resp.status_code < 400
        except httpx.HTTPError:
            return False

    # -- Heartbeat runs ------------------------------------------------------

    async def list_runs(
        self,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agentId"] = agent_id

        resp = await self._client.get(
            f"{self.company_url}/heartbeat-runs", params=params
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "runs" in data:
            return data["runs"]
        return data if isinstance(data, list) else []

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        try:
            resp = await self._client.get(f"{self.base_url}/api/heartbeat-runs/{run_id}")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return None

    async def get_run_log(self, run_id: str) -> str:
        try:
            resp = await self._client.get(
                f"{self.base_url}/api/heartbeat-runs/{run_id}/log"
            )
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError:
            return ""
