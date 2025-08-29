"""This module manages setting and getting the API key."""

import os
from pathlib import Path
import tomllib

import click
import tomli_w

APP_NAME = "auto_detail"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.toml"
ENV_VAR = "GEMINI_API_KEY"


def get_api_key(cli_key: str | None = None) -> str:
    """Resolve API key from CLI arg, env var, or config file. Prompt if missing."""
    if cli_key:
        return cli_key

    if env_key := os.getenv(ENV_VAR):
        return env_key

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as f:
            config = tomllib.load(f)
            if "api_key" in config:
                return config["api_key"]

    key = click.prompt(
        "No API key found. Please set your Google Gemini API key", hide_input=True
    ).strip()
    set_api_key(key)
    return key


def set_api_key(key: str):
    """Save API key to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump({"api_key": key}, f)
    click.echo(f"✔ API key saved to {CONFIG_FILE}")
