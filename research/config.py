from __future__ import annotations
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")
    notion_token: str | None = os.getenv("NOTION_TOKEN")
    notion_database_id: str | None = os.getenv("NOTION_DATABASE_ID")
    notion_version: str = os.getenv("NOTION_VERSION", "2025-09-03")
    default_out_dir: str = os.getenv("DEFAULT_OUT_DIR", "out")

settings = Settings()
