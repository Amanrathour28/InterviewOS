"""Prompts package — auto-registers all templates on import."""

from app.prompts.registry import register, get, get_latest, list_prompts
from app.prompts import templates  # noqa: F401 — side effect: registers all templates

__all__ = ["register", "get", "get_latest", "list_prompts"]
