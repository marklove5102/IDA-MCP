"""Reusable utility widgets for the settings page."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()
