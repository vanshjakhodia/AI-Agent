"""Configuration manager for the AI Email Agent."""

from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Automatically load .env file if present
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


@dataclass
class AgentConfig:
    # LLM Settings
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto").lower()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")

    # SMTP / Gmail Settings
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    sender_name: str = os.getenv("SENDER_NAME", "AI Agent")
    sender_email: str = os.getenv("SENDER_EMAIL", os.getenv("SMTP_USER", ""))

    # Behavioral & Guardrails
    # If dry_run is True, email sending is simulated safely
    dry_run: bool = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
    require_confirmation: bool = os.getenv("REQUIRE_CONFIRMATION", "true").lower() in ("true", "1", "yes")

    # Storage paths
    data_dir: Path = BASE_DIR / "data"
    contacts_file: Path = BASE_DIR / "data" / "contacts.json"
    audit_file: Path = BASE_DIR / "data" / "sent_history.json"
    outbox_dir: Path = BASE_DIR / "data" / "outbox"

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)


config = AgentConfig()
