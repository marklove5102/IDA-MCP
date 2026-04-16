"""Simple importable supervisor API."""

from __future__ import annotations

from .manager import SupervisorManager


def create_manager() -> SupervisorManager:
    return SupervisorManager()
