"""Configuration for the eval-runner."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class EvalConfig:
    paperclip_url: str = field(default_factory=lambda: os.getenv("PAPERCLIP_API_URL", "http://localhost:3100"))
    company_id: str = field(default_factory=lambda: os.getenv("PAPERCLIP_COMPANY_ID", ""))
    architect_agent_id: str = field(default_factory=lambda: os.getenv("ARCHITECT_AGENT_ID", ""))
    architect_dir: Path = field(
        default_factory=lambda: Path(os.getenv("ARCHITECT_DIR", "")).expanduser()
    )
    theme_dir: Path = field(
        default_factory=lambda: Path(os.getenv("THEME_DIR", "")).expanduser()
    )
    eval_runner_agent_id: str = field(
        default_factory=lambda: os.getenv("EVAL_RUNNER_AGENT_ID", "")
    )
    max_cases: int = field(default_factory=lambda: int(os.getenv("MAX_CASES", "40")))
    timeout_per_case_min: int = field(
        default_factory=lambda: int(os.getenv("TIMEOUT_PER_CASE_MIN", "3"))
    )

    @property
    def results_dir(self) -> Path:
        return Path(__file__).resolve().parent / "results"

    @property
    def eval_cases_dir(self) -> Path:
        return Path(__file__).resolve().parent / "eval_cases"


config = EvalConfig()
