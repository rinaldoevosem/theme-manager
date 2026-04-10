"""Configuration for the Shopify Theme Architect agent."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PLACEHOLDER_TOKENS = {"", "dry-run-token", "your_shopify_access_token", "your_github_token"}

PROJECTS_ROOT = Path(__file__).resolve().parent.parent  # /Users/melo/shopify-theme/


def store_slug_from_domain(domain: str) -> str:
    """Extract the store slug from a Shopify domain.

    'horizon-clone.myshopify.com' -> 'horizon-clone'
    """
    domain = domain.strip().lower().rstrip("/")
    if "://" in domain:
        domain = domain.split("://", 1)[1]
    if domain.endswith(".myshopify.com"):
        return domain.removesuffix(".myshopify.com")
    return domain.split(".")[0]


@dataclass
class Config:
    """Central configuration loaded from environment variables."""

    shopify_store_domain: str = field(default_factory=lambda: os.getenv("SHOPIFY_STORE_DOMAIN", ""))
    shopify_access_token: str = field(default_factory=lambda: os.getenv("SHOPIFY_ACCESS_TOKEN", ""))
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    github_owner: str = field(default_factory=lambda: os.getenv("GITHUB_OWNER", ""))
    paperclip_api_url: str = field(default_factory=lambda: os.getenv("PAPERCLIP_API_URL", "http://localhost:3100"))
    paperclip_agent_id: str = field(default_factory=lambda: os.getenv("PAPERCLIP_AGENT_ID", "theme-architect"))
    paperclip_api_key: str = field(default_factory=lambda: os.getenv("PAPERCLIP_API_KEY", ""))
    paperclip_company_id: str = field(default_factory=lambda: os.getenv("PAPERCLIP_COMPANY_ID", ""))
    shopify_dev_mcp_path: str = field(default_factory=lambda: os.getenv("SHOPIFY_DEV_MCP_PATH", ""))
    project_dir: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, project_dir: Path | None = None) -> "Config":
        """Load config from a specific project directory's .env file."""
        if project_dir is not None:
            env_file = project_dir / ".env"
            if env_file.exists():
                load_dotenv(env_file, override=True)
        else:
            load_dotenv()
        cfg = cls()
        cfg.project_dir = project_dir
        return cfg

    def has_valid_credentials(self) -> bool:
        """Check whether Shopify and GitHub credentials are real (not placeholders)."""
        return (
            self.shopify_store_domain.strip().lower() not in _PLACEHOLDER_TOKENS
            and self.shopify_access_token.strip() not in _PLACEHOLDER_TOKENS
            and self.github_token.strip() not in _PLACEHOLDER_TOKENS
        )

    @property
    def github_repo(self) -> str:
        """Single GitHub repo for all environments (branches differentiate them)."""
        return os.getenv("GITHUB_REPO") or os.getenv("GITHUB_REPO_MAIN", "")

    @property
    def theme_repo_dir(self) -> Path | None:
        """Path to the theme repo directory for the current store."""
        if self.project_dir:
            return self.project_dir / "repo-main"
        if self.shopify_store_domain:
            slug = store_slug_from_domain(self.shopify_store_domain)
            return PROJECTS_ROOT / slug / "repo-main"
        return None


config = Config()
