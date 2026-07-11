"""Application configuration via Pydantic Settings.

All values can be overridden through environment variables or a local `.env`
file (see `.env.example`). Keep this lightweight so the API boots on low-end
machines without optional heavy dependencies.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # Disable JSON decoding at the env-source level so CORS_ORIGINS can be
        # supplied as a plain comma-separated string (parsed by the validator
        # below). Without this, pydantic-settings tries json.loads first and
        # raises on a non-JSON value. CORS_ORIGINS is the only complex field.
        enable_decoding=False,
    )

    # --- App ---
    APP_NAME: str = "Miori Core"
    APP_VERSION: str = "1.1.0"
    DEBUG: bool = True

    # --- Server ---
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./miori.db"

    # --- CORS ---
    # Comma-separated list in env, e.g. "http://localhost:3000,http://localhost:1420".
    # Default to explicit localhost dev origins (NOT "*") so allow_credentials
    # stays safe; override via CORS_ORIGINS for other setups.
    CORS_ORIGINS: list[str] = [
        # Desktop (Tauri/Vite strictPort 1420) + remote dashboard (5174),
        # plus the generic Vite 5173 for flexibility.
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    # --- Feature flags ---
    # When True, remote dashboard / device sync endpoints are active.
    # TODO(Mark-XLVI): wire real remote session transport when enabled.
    REMOTE_ENABLED: bool = True

    # Lite mode keeps optional heavy deps (vector stores, embeddings, real model
    # providers) lazy/disabled so Miori stays usable on low-end machines.
    LITE_MODE: bool = True

    # If set, enforces Bearer token auth in get_current_user. If None, open.
    MIORI_API_TOKEN: str | None = None

    # When True, MemoryService uses embedding + vector search.
    SEMANTIC_MEMORY_ENABLED: bool = False

    # When True, allows the computer-use tool to be armed and used.
    # [ARCH-CRITICAL] Off by default for safety.
    COMPUTER_USE_ENABLED: bool = False

    # When True, allows the computer-use tool to execute shell commands.
    # Must also have COMPUTER_USE_ENABLED=True.
    COMPUTER_USE_SHELL_ENABLED: bool = False

    # When True, the APScheduler background task system is spun up.
    SCHEDULER_ENABLED: bool = True

    # Semantic memory model (used only when LITE_MODE is off). Small + CPU-friendly.
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Orchestrator ---
    # When true, ChatService routes through the LiteLLM orchestrator instead of
    # a single adapter. Falls back to registry/mock on pool exhaustion.
    ORCHESTRATOR_ENABLED: bool = False

    # Max cross-provider failover attempts before exhausting to mock.
    ORCHESTRATOR_MAX_FAILOVERS: int = 3

    # Request timeout (seconds) passed to LiteLLM.
    ORCHESTRATOR_TIMEOUT_S: int = 30

    # Add jitter to Retry-After when honoring backoff.
    ORCHESTRATOR_RETRY_AFTER_JITTER: bool = True

    # --- Paths ---
    # Location of shared prompt profiles in the monorepo. Persona service degrades
    # gracefully if this path is missing.
    PROMPTS_DIR: str = "../../packages/prompts"
    UPLOAD_DIR: str = "./data/uploads"

    # --- Uploads ---
    # Max upload size in bytes (default 25 MB). Enforced by the files router.
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024

    # --- Providers ---
    # Active model provider name; persisted via SettingsService and read back at
    # startup. Falls back to "mock" if the selected provider has no API key.
    DEFAULT_PROVIDER: str = "mock"

    # OpenAI / OpenAI-compatible (OpenRouter, local servers, …).
    OPENAI_API_KEY: str | None = None
    OPENAI_API_KEYS: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Google Gemini (GEMINI_API_KEY preferred; GOOGLE_API_KEY accepted as alias).
    GEMINI_API_KEY: str | None = None
    GEMINI_API_KEYS: str | None = None
    GOOGLE_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    @property
    def gemini_key(self) -> str | None:
        """Effective Gemini key (GEMINI_API_KEY wins, GOOGLE_API_KEY fallback)."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    # Groq (OpenAI-compatible).
    GROQ_API_KEY: str | None = None
    GROQ_API_KEYS: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Mistral (OpenAI-compatible).
    MISTRAL_API_KEY: str | None = None
    MISTRAL_API_KEYS: str | None = None
    MISTRAL_MODEL: str = "mistral-small-latest"

    # SambaNova (OpenAI-compatible).
    SAMBANOVA_API_KEY: str | None = None
    SAMBANOVA_API_KEYS: str | None = None
    SAMBANOVA_MODEL: str = "Meta-Llama-3.1-8B-Instruct"

    # OpenRouter (OpenAI-compatible).
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_API_KEYS: str | None = None
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"

    # Hugging Face Inference.
    HUGGINGFACE_API_KEY: str | None = None
    HUGGINGFACE_API_KEYS: str | None = None
    HUGGINGFACE_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"

    # Cohere.
    COHERE_API_KEY: str | None = None
    COHERE_API_KEYS: str | None = None
    COHERE_MODEL: str = "command-r"

    # Cloudflare Workers AI.
    CLOUDFLARE_API_KEY: str | None = None
    CLOUDFLARE_API_KEYS: str | None = None
    CLOUDFLARE_ACCOUNT_ID: str | None = None
    CLOUDFLARE_MODEL: str = "@cf/meta/llama-3.1-8b-instruct"

    def _resolve_api_keys(self, single: str | None, plural: str | None) -> list[str]:
        raw = plural or single
        if not raw:
            return []
        parts = [k.strip() for k in raw.split(",")]
        return [k for k in parts if k]

    def openai_keys(self) -> list[str]:
        return self._resolve_api_keys(self.OPENAI_API_KEY, self.OPENAI_API_KEYS)

    def gemini_keys(self) -> list[str]:
        return self._resolve_api_keys(self.GEMINI_API_KEY, self.GEMINI_API_KEYS)

    def groq_keys(self) -> list[str]:
        return self._resolve_api_keys(self.GROQ_API_KEY, self.GROQ_API_KEYS)

    def mistral_keys(self) -> list[str]:
        return self._resolve_api_keys(self.MISTRAL_API_KEY, self.MISTRAL_API_KEYS)

    def sambanova_keys(self) -> list[str]:
        return self._resolve_api_keys(self.SAMBANOVA_API_KEY, self.SAMBANOVA_API_KEYS)

    def openrouter_keys(self) -> list[str]:
        return self._resolve_api_keys(self.OPENROUTER_API_KEY, self.OPENROUTER_API_KEYS)

    def huggingface_keys(self) -> list[str]:
        return self._resolve_api_keys(self.HUGGINGFACE_API_KEY, self.HUGGINGFACE_API_KEYS)

    def cohere_keys(self) -> list[str]:
        return self._resolve_api_keys(self.COHERE_API_KEY, self.COHERE_API_KEYS)

    def cloudflare_keys(self) -> list[str]:
        return self._resolve_api_keys(self.CLOUDFLARE_API_KEY, self.CLOUDFLARE_API_KEYS)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()


settings = get_settings()

_TRUTHY = {"1", "true", "yes", "on"}


def get_effective_bool(db: object | None, key: str, default: bool) -> bool:
    """Resolve a boolean flag: DB setting (runtime) overrides env (default).

    ``db`` is an optional SQLAlchemy Session. When provided and the key exists in
    the ``settings`` table, that value wins; otherwise the env/default is used.
    Lazy-imports SettingsService to avoid an import cycle.
    """
    if db is not None:
        try:
            from app.services.settings_service import SettingsService

            raw = SettingsService(db).get(key)  # type: ignore[arg-type]
            if raw is not None:
                return str(raw).strip().lower() in _TRUTHY
        except Exception:  # noqa: BLE001 - never let config resolution crash
            pass
    return default
