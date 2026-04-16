"""Modern theme for the IDE.

Provides a centralized theme module with light (default) and dark palettes.
Uses a subtle blue accent color for interactive elements while keeping
a clean, professional monochrome base. All UI colors, fonts, and QSS
are defined here to keep widgets free of hard-coded styling.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class ThemeMode(Enum):
    LIGHT = auto()
    DARK = auto()


@dataclass(frozen=True, slots=True)
class _Palette:
    """A single color palette."""

    # Backgrounds
    window_bg: str
    panel_bg: str
    sidebar_bg: str
    input_bg: str
    hover_bg: str
    selected_bg: str

    # Text
    text_primary: str
    text_secondary: str
    accent_text: str

    # Borders / accents
    border: str
    border_light: str
    accent: str
    accent_hover: str
    accent_subtle: str
    button_bg: str
    button_border: str
    button_text: str

    # Status
    status_ok: str
    status_warning: str
    status_error: str
    status_unknown: str

    # Misc
    splitter: str
    header_bg: str


class Theme:
    """Modern theme with blue accent."""

    _LIGHT = _Palette(
        window_bg="#f8f9fa",
        panel_bg="#ffffff",
        sidebar_bg="#f0f1f3",
        input_bg="#ffffff",
        hover_bg="#e9ecef",
        selected_bg="#3b82f6",
        text_primary="#1a1a2e",
        text_secondary="#6b7280",
        accent_text="#ffffff",
        border="#e2e5e9",
        border_light="#f0f1f3",
        accent="#3b82f6",
        accent_hover="#2563eb",
        accent_subtle="#eff6ff",
        button_bg="#ffffff",
        button_border="#d1d5db",
        button_text="#374151",
        status_ok="#059669",
        status_warning="#d97706",
        status_error="#dc2626",
        status_unknown="#9ca3af",
        splitter="#e2e5e9",
        header_bg="#f8f9fa",
    )

    _DARK = _Palette(
        window_bg="#0f1117",
        panel_bg="#1a1d27",
        sidebar_bg="#141620",
        input_bg="#1e2130",
        hover_bg="#262a3a",
        selected_bg="#3b82f6",
        text_primary="#e5e7eb",
        text_secondary="#9ca3af",
        accent_text="#ffffff",
        border="#2d3148",
        border_light="#232738",
        accent="#3b82f6",
        accent_hover="#60a5fa",
        accent_subtle="#1e2a4a",
        button_bg="#232738",
        button_border="#3d4258",
        button_text="#e5e7eb",
        status_ok="#34d399",
        status_warning="#fbbf24",
        status_error="#f87171",
        status_unknown="#6b7280",
        splitter="#2d3148",
        header_bg="#141620",
    )

    def __init__(self, mode: ThemeMode) -> None:
        self.mode = mode
        self._palette = self._LIGHT if mode == ThemeMode.LIGHT else self._DARK

    # ------------------------------------------------------------------ #
    # Convenience accessors
    # ------------------------------------------------------------------ #
    @property
    def window_bg(self) -> str:
        return self._palette.window_bg

    @property
    def panel_bg(self) -> str:
        return self._palette.panel_bg

    @property
    def text_primary(self) -> str:
        return self._palette.text_primary

    @property
    def text_secondary(self) -> str:
        return self._palette.text_secondary

    @property
    def accent(self) -> str:
        return self._palette.accent

    # ------------------------------------------------------------------ #
    # Stylesheet generation
    # ------------------------------------------------------------------ #
    def stylesheet(self) -> str:
        c = self._palette
        return f"""
        /* ---- Global window ---- */
        QMainWindow {{
            background: {c.window_bg};
            color: {c.text_primary};
            font-family: "Segoe UI", "SF Pro Text", "Inter", sans-serif;
        }}

        QWidget {{
            font-family: "Segoe UI", "SF Pro Text", "Inter", sans-serif;
        }}

        /* ---- Activity bar (sidebar icons) ---- */
        #activityBar {{
            background: {c.sidebar_bg};
            border: none;
            border-right: 1px solid {c.border};
        }}
        QToolButton#activityButton {{
            background: transparent;
            border: none;
            border-radius: 8px;
            padding: 9px;
            color: {c.text_secondary};
        }}
        QToolButton#activityButton:hover {{
            background: {c.hover_bg};
            color: {c.text_primary};
        }}
        QToolButton#activityButton[active="true"] {{
            background: {c.accent_subtle};
            color: {c.accent};
        }}

        /* ---- Panels ---- */
        QFrame#panel {{
            background: {c.panel_bg};
            border: 1px solid {c.border};
            border-radius: 10px;
        }}
        QLabel#panelTitle {{
            color: {c.text_primary};
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }}

        /* ---- Settings page typography ---- */
        QLabel#settingsTitle {{
            color: {c.text_primary};
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.01em;
            padding-bottom: 4px;
        }}
        QFrame#settingsGroup {{
            background: {c.panel_bg};
            border: 1px solid {c.border};
            border-radius: 10px;
            padding: 4px;
        }}
        QLabel#settingsGroupTitle {{
            color: {c.text_primary};
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }}
        QLabel#settingsGroupDescription {{
            color: {c.text_secondary};
            font-size: 12px;
            line-height: 1.4;
        }}
        QLabel#settingsFieldLabel {{
            color: {c.text_primary};
            font-weight: 600;
            font-size: 12px;
        }}
        QLabel#settingsFieldDescription {{
            color: {c.text_secondary};
            font-size: 11px;
        }}
        QLabel#settingsHint {{
            color: {c.text_secondary};
            font-size: 11px;
            font-style: italic;
        }}

        /* ---- Inputs ---- */
        QTreeWidget, QTextEdit, QLineEdit, QListWidget, QSpinBox, QComboBox, QTableWidget {{
            background: {c.input_bg};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 6px;
            padding: 6px 8px;
            selection-background-color: {c.accent};
            selection-color: {c.accent_text};
            font-size: 13px;
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border: 2px solid {c.accent};
            padding: 5px 7px;
            background: {c.accent_subtle};
        }}
        QLineEdit:read-only {{
            background: {c.border_light};
            color: {c.text_secondary};
        }}

        /* ---- Status cards ---- */
        QFrame#statusCard {{
            background: {c.panel_bg};
            border: 1px solid {c.border};
            border-radius: 10px;
            border-left: 4px solid {c.border};
        }}
        QFrame#statusCard[state="ok"] {{
            border-left: 4px solid {c.status_ok};
        }}
        QFrame#statusCard[state="warning"] {{
            border-left: 4px solid {c.status_warning};
        }}
        QFrame#statusCard[state="error"] {{
            border-left: 4px solid {c.status_error};
        }}
        QFrame#statusCard[state="unknown"] {{
            border-left: 4px solid {c.status_unknown};
        }}
        QLabel#statusCardTitle {{
            color: {c.text_primary};
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.01em;
        }}
        QLabel#statusState[state="ok"] {{
            color: {c.status_ok};
            font-weight: 700;
            font-size: 13px;
        }}
        QLabel#statusState[state="warning"] {{
            color: {c.status_warning};
            font-weight: 700;
            font-size: 13px;
        }}
        QLabel#statusState[state="error"] {{
            color: {c.status_error};
            font-weight: 700;
            font-size: 13px;
        }}
        QLabel#statusState[state="unknown"] {{
            color: {c.status_unknown};
            font-weight: 600;
            font-size: 13px;
        }}

        /* ---- Table header ---- */
        QHeaderView::section {{
            background: {c.header_bg};
            color: {c.text_secondary};
            border: none;
            border-bottom: 1px solid {c.border};
            padding: 8px 6px;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        /* ---- Buttons ---- */
        QPushButton {{
            background: {c.button_bg};
            color: {c.button_text};
            border: 1px solid {c.button_border};
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: {c.hover_bg};
            border: 1px solid {c.text_secondary};
        }}
        QPushButton:pressed {{
            background: {c.accent_subtle};
            border: 1px solid {c.accent};
            color: {c.accent};
        }}

        /* Primary action buttons */
        QPushButton#primaryButton {{
            background: {c.accent};
            color: {c.accent_text};
            border: 1px solid {c.accent};
            font-weight: 600;
        }}
        QPushButton#primaryButton:hover {{
            background: {c.accent_hover};
            border: 1px solid {c.accent_hover};
        }}
        QPushButton#primaryButton:pressed {{
            background: {c.text_primary};
            border: 1px solid {c.text_primary};
        }}

        /* ---- Tool buttons (expand toggles) ---- */
        QToolButton {{
            background: transparent;
            color: {c.text_secondary};
            border: 1px solid transparent;
            border-radius: 6px;
            font-weight: 600;
            font-size: 12px;
            padding: 6px 10px;
        }}
        QToolButton:hover {{
            background: {c.hover_bg};
            color: {c.text_primary};
            border: 1px solid {c.border};
        }}
        QToolButton:checked {{
            color: {c.accent};
            background: {c.accent_subtle};
            border: 1px solid {c.accent};
        }}

        /* ---- Menus / category list ---- */
        QMenuBar {{
            background: {c.panel_bg};
            color: {c.text_primary};
            border: none;
            border-bottom: 1px solid {c.border};
            padding: 2px;
        }}
        QMenu {{
            background: {c.panel_bg};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 8px;
            padding: 4px;
        }}
        QMenuBar::item:selected {{
            background: {c.accent_subtle};
            color: {c.accent};
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background: {c.accent};
            color: {c.accent_text};
            border-radius: 4px;
        }}
        QListWidget#settingsCategoryList {{
            background: {c.sidebar_bg};
            color: {c.text_primary};
            border: none;
            border-right: 1px solid {c.border};
            outline: none;
            padding: 8px 4px;
        }}
        QListWidget#settingsCategoryList::item {{
            padding: 10px 12px;
            border-radius: 6px;
            margin: 2px 4px;
            font-weight: 500;
            font-size: 13px;
        }}
        QListWidget#settingsCategoryList::item:selected {{
            background: {c.accent};
            color: {c.accent_text};
        }}
        QListWidget#settingsCategoryList::item:hover:!selected {{
            background: {c.hover_bg};
        }}

        /* ---- Status bar ---- */
        QStatusBar {{
            background: {c.sidebar_bg};
            color: {c.text_secondary};
            border-top: 1px solid {c.border};
            font-size: 12px;
            padding: 2px 8px;
        }}

        /* ---- Splitter ---- */
        QSplitter::handle {{
            background: {c.splitter};
            width: 1px;
            height: 1px;
        }}
        QSplitter::handle:hover {{
            background: {c.accent};
        }}

        /* ---- Checkbox ---- */
        QCheckBox {{
            color: {c.text_primary};
            font-size: 13px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {c.border};
            border-radius: 4px;
            background: {c.input_bg};
        }}
        QCheckBox::indicator:hover {{
            border: 2px solid {c.accent};
        }}
        QCheckBox::indicator:checked {{
            background: {c.accent};
            border: 2px solid {c.accent};
            image: none;
        }}

        /* ---- Scroll area ---- */
        QScrollArea {{
            border: none;
            background: transparent;
        }}

        /* ---- Scrollbar ---- */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c.border};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c.text_secondary};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {c.border};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {c.text_secondary};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        /* ---- Tab bar (QTabBar in QTabWidget) ---- */
        QTabWidget::pane {{
            border: 1px solid {c.border};
            border-radius: 8px;
            background: {c.panel_bg};
        }}
        QTabBar::tab {{
            background: transparent;
            color: {c.text_secondary};
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 13px;
        }}
        QTabBar::tab:selected {{
            color: {c.accent};
            border-bottom: 2px solid {c.accent};
        }}
        QTabBar::tab:hover:!selected {{
            color: {c.text_primary};
            border-bottom: 2px solid {c.border};
        }}

        /* ---- ToolTip ---- */
        QToolTip {{
            background: {c.panel_bg};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}

        /* ---- MessageBox ---- */
        QMessageBox {{
            background: {c.panel_bg};
        }}
        """

    @classmethod
    def light(cls) -> "Theme":
        return cls(ThemeMode.LIGHT)

    @classmethod
    def dark(cls) -> "Theme":
        return cls(ThemeMode.DARK)
