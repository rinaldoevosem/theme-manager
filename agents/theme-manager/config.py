"""Configuration for the Shopify Theme Manager agent."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PLACEHOLDER_TOKENS = {"", "dry-run-token", "your_shopify_access_token", "your_github_token"}


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
class ThemeEnvironment:
    """Represents a single Shopify theme environment."""

    name: str
    github_repo: str
    shopify_theme_id: str
    branch: str
    description: str


@dataclass
class Config:
    """Central configuration loaded from environment variables."""

    shopify_store_domain: str = field(default_factory=lambda: os.getenv("SHOPIFY_STORE_DOMAIN", ""))
    shopify_access_token: str = field(default_factory=lambda: os.getenv("SHOPIFY_ACCESS_TOKEN", ""))
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    github_owner: str = field(default_factory=lambda: os.getenv("GITHUB_OWNER", ""))
    paperclip_api_url: str = field(default_factory=lambda: os.getenv("PAPERCLIP_API_URL", "http://localhost:3100"))
    paperclip_agent_id: str = field(default_factory=lambda: os.getenv("PAPERCLIP_AGENT_ID", "theme-manager"))
    paperclip_api_key: str = field(default_factory=lambda: os.getenv("PAPERCLIP_API_KEY", ""))
    paperclip_company_id: str = field(default_factory=lambda: os.getenv("PAPERCLIP_COMPANY_ID", ""))
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
    def environments(self) -> dict[str, ThemeEnvironment]:
        repo = self.github_repo
        return {
            "main": ThemeEnvironment(
                name="main",
                github_repo=repo,
                shopify_theme_id=os.getenv("SHOPIFY_THEME_ID_MAIN", ""),
                branch="main",
                description="Published production theme — live on the storefront.",
            ),
            "staging": ThemeEnvironment(
                name="staging",
                github_repo=repo,
                shopify_theme_id=os.getenv("SHOPIFY_THEME_ID_STAGING", ""),
                branch="staging",
                description="Client review environment — approved changes awaiting go-live.",
            ),
            "dev": ThemeEnvironment(
                name="dev",
                github_repo=repo,
                shopify_theme_id=os.getenv("SHOPIFY_THEME_ID_DEV", ""),
                branch="dev",
                description="Active development — new features, bug fixes, and experiments.",
            ),
        }


config = Config()
