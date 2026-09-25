"""
Central configuration for the Multi-Agent RAG System.

All environment-dependent values (API keys, paths, model names, tuning
parameters) are loaded here from environment variables / a .env file, so the
rest of the codebase never touches os.environ directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env once, on first import of this module.
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_path(name: str, default: str) -> Path:
    return (PROJECT_ROOT / os.getenv(name, default)).resolve()


@dataclass
class Settings:
    # --- API access ---
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_llm_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_LLM_MODEL", "gemini-3.8-flash")
    )
    gemini_embedding_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    )

    # --- Paths ---
    chroma_persist_dir: Path = field(
        default_factory=lambda: _env_path("CHROMA_PERSIST_DIR", "./data/chroma")
    )
    sqlite_db_path: Path = field(
        default_factory=lambda: _env_path("SQLITE_DB_PATH", "./data/enterprise.db")
    )
    docs_dir: Path = field(default_factory=lambda: _env_path("DOCS_DIR", "./data/docs"))

    # --- Retrieval tuning ---
    rag_top_k: int = field(default_factory=lambda: int(os.getenv("RAG_TOP_K", "4")))
    rag_relevance_threshold: float = field(
        default_factory=lambda: float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.35"))
    )

    # --- Logging ---
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: Path = field(default_factory=lambda: _env_path("LOG_FILE", "./logs/app.log"))

    def require_api_key(self) -> str:
        if not self.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        return self.gemini_api_key


settings = Settings()