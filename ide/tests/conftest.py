from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure the ide/ directory is importable
ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

# Force offscreen Qt rendering so UI tests run headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Provide a singleton QApplication for all UI tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
