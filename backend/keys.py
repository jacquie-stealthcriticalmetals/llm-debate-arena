import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent / ".env"

KEY_NAMES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def load_keys():
    load_dotenv(ENV_PATH, override=True)


def get_key(provider: str) -> str | None:
    load_keys()
    env_name = KEY_NAMES.get(provider)
    if not env_name:
        return None
    return os.environ.get(env_name)


def get_configured_providers() -> dict[str, bool]:
    load_keys()
    return {provider: bool(os.environ.get(env_name)) for provider, env_name in KEY_NAMES.items()}


def save_keys(keys: dict[str, str]):
    existing = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    for provider, value in keys.items():
        env_name = KEY_NAMES.get(provider)
        if env_name and value:
            existing[env_name] = value

    lines = [f"{k}={v}" for k, v in existing.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n")
    load_keys()
