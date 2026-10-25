"""All settings come from here. Environment variables use the SS_ prefix."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SS_", env_file=".env", extra="ignore")

    # Gemma through Ollama: check-in reader and Slumbrock's lines.
    ollama_url: str = "http://localhost:11434"
    model: str = "gemma3:1b"
    llm_timeout_s: float = 60.0
    llm_num_predict: int = 240
    llm_num_thread: int | None = None

    # Steps cap (the "receiver window"). See specs/001-slow-start-mvp/design.md section 3.
    cap_quantile: float = 0.30
    cap_min_days: int = 7
    prior_rows: int = 400
    tabpfn_estimators: int = 4
    use_tabpfn: bool = True
    feature_set: str = "v1"  # v2 is chosen on a validation window; see results/

    # Requests per minute per client for the routes that cost CPU (goal, check-in).
    rate_per_minute: int = 30

    # Serving the built app from the same process.
    static_dir: str = "../app/dist"
    cors_origins: str = "*"

    @property
    def ollama_base(self) -> str:
        base = self.ollama_url.rstrip("/")
        return base if "://" in base else f"http://{base}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
