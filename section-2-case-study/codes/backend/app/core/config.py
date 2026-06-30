from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT_DIR / "config.yaml"


def _load_root_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        import yaml

        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except ModuleNotFoundError:
        return _parse_simple_yaml(CONFIG_PATH.read_text(encoding="utf-8"))


def _parse_simple_yaml(text: str) -> dict:
    config: dict[str, dict | str] = {}
    current_section: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and line.endswith(":"):
            section_name = line[:-1].strip()
            current_section = {}
            config[section_name] = current_section
            continue
        if current_section is not None and line.startswith("  ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current_section[key.strip()] = value.strip().strip("'\"")
    return config


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_setting(value: object, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


_ROOT_CONFIG = _load_root_config()
_MODEL_CONFIG = _ROOT_CONFIG.get("model", {})


@dataclass(frozen=True)
class ModelSettings:
    provider: str
    base_url: str
    model: str
    timeout_seconds: float


def get_model_settings() -> ModelSettings:
    root_config = _load_root_config()
    model_config = root_config.get("model", {})
    provider = os.getenv("MODEL_PROVIDER", model_config.get("provider", "lm-studio"))
    base_url = os.getenv("MODEL_BASE_URL", model_config.get("llm_endpoint", "http://localhost:1234/v1"))
    model = os.getenv("MODEL_NAME", model_config.get("name", "qwen/qwen3.6-35b-a3b"))
    timeout_seconds = _float_setting(os.getenv("MODEL_TIMEOUT_SECONDS", model_config.get("timeout_seconds", 60.0)), 60.0)
    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", model_config.get("ollama_endpoint", base_url))
        model = os.getenv("OLLAMA_MODEL", model_config.get("ollama_model", model))
    return ModelSettings(provider=provider, base_url=base_url, model=model, timeout_seconds=timeout_seconds)


def save_model_settings(provider: str, base_url: str, model: str, timeout_seconds: float | None = None) -> ModelSettings:
    root_config = _load_root_config()
    model_config = dict(root_config.get("model", {}))
    model_config["provider"] = provider
    model_config["llm_endpoint"] = base_url
    model_config["name"] = model
    if timeout_seconds is not None:
        model_config["timeout_seconds"] = _float_setting(timeout_seconds, 60.0)
    if provider == "ollama":
        model_config["ollama_endpoint"] = base_url
        model_config["ollama_model"] = model
    root_config["model"] = model_config
    _write_root_config(root_config)
    return ModelSettings(
        provider=provider,
        base_url=base_url,
        model=model,
        timeout_seconds=_float_setting(model_config.get("timeout_seconds", 60.0), 60.0),
    )


def _write_root_config(config: dict) -> None:
    try:
        import yaml

        CONFIG_PATH.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    except ModuleNotFoundError:
        lines: list[str] = []
        for section, values in config.items():
            if isinstance(values, dict):
                lines.append(f"{section}:")
                for key, value in values.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append(f"{section}: {values}")
        CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    history_syllabus_year: int = int(os.getenv("HISTORY_SYLLABUS_YEAR", "2026"))
    history_syllabus_pdf_url: str = os.getenv(
        "HISTORY_SYLLABUS_PDF_URL",
        "https://isomer-user-content.by.gov.sg/334/3622b032-4be0-497a-9192-399cb6c98b65/2174_y26_sy.pdf",
    )
    model_provider: str = os.getenv("MODEL_PROVIDER", _MODEL_CONFIG.get("provider", "lm-studio"))
    model_base_url: str = os.getenv("MODEL_BASE_URL", _MODEL_CONFIG.get("llm_endpoint", "http://localhost:1234/v1"))
    model_name: str = os.getenv("MODEL_NAME", _MODEL_CONFIG.get("name", "qwen/qwen3.6-35b-a3b"))
    model_timeout_seconds: float = _float_setting(os.getenv("MODEL_TIMEOUT_SECONDS", _MODEL_CONFIG.get("timeout_seconds", 60.0)), 60.0)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", _MODEL_CONFIG.get("ollama_endpoint", "http://localhost:11434"))
    ollama_model: str = os.getenv("OLLAMA_MODEL", _MODEL_CONFIG.get("ollama_model", "qwen2.5vl:latest"))
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
    analysis_cache_enabled: bool = _env_bool("ANALYSIS_CACHE_ENABLED", False)
    admin_token: str = os.getenv("ADMIN_TOKEN", "")
    root_dir: Path = ROOT_DIR

    @property
    def data_dir(self) -> Path:
        return self.root_dir / "data"


settings = Settings()
