"""Main window for the PySide6 IDE MVP."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QSize, Qt, QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.i18n import I18n, normalize_language
from app.ui.icons import make_sidebar_icons
from app.presenters.main_window_presenter import (
    STATUS_CARD_TITLE_KEYS,
    MainWindowViewModel,
    StatusCardViewModel,
    TreeRowViewModel,
    build_main_window_view_model,
)
from app.services.supervisor_client import SupervisorClient
from supervisor.models import SupervisorSnapshot
from app.ui.settings import SettingsPage
from app.ui.theme import Theme
from app.ui.workspace.directory_tree import DirectoryTreeWidget
from app.ui.workspace.hex_view import HexViewWidget
from app.ui.workspace.code_view import CodeViewWidget


SIDEBAR_ITEMS = (
    ("chat", "sidebar.chat"),
    ("fs", "sidebar.fs"),
    ("settings", "sidebar.settings"),
    ("status", "sidebar.status"),
)


class _GatewayWorker(QThread):
    progress = Signal(str)
    finished = Signal(object)  # SupervisorSnapshot

    def __init__(self, action: str, supervisor_client, parent=None) -> None:
        super().__init__(parent)
        self._action = action
        self._supervisor_client = supervisor_client

    def run(self) -> None:
        from supervisor.gateway_controller import GatewayController

        controller = GatewayController(log=self.progress.emit)

        try:
            if self._action == "refresh":
                self.progress.emit("--- Refreshing status ---")
                controller.status()
            elif self._action == "start":
                self.progress.emit("--- Starting gateway ---")
                controller.start()
            elif self._action == "stop":
                self.progress.emit("--- Stopping gateway ---")
                controller.stop()
            self.progress.emit("--- Refreshing final status ---")
            self.finished.emit(self._supervisor_client.get_snapshot())
        except Exception as exc:
            self.progress.emit(f"Error: {exc}")
            try:
                self.finished.emit(self._supervisor_client.get_snapshot())
            except Exception:
                self.finished.emit(None)


class MainWindow(QMainWindow):
    def __init__(self, supervisor_client: SupervisorClient | None = None) -> None:
        super().__init__()
        self.supervisor_client = supervisor_client or SupervisorClient()
        self._language = self._load_language()
        self._i18n = I18n(self._language)
        self._snapshot: SupervisorSnapshot | None = None

        self._activity_items: dict[str, QToolButton] = {}
        self._panel_labels: dict[str, QLabel] = {}
        self._status_card_titles: dict[str, QLabel] = {}
        self._status_buttons: dict[str, QPushButton] = {}
        self._menu_actions: dict[str, QAction] = {}

        self.resize(1520, 960)

        self._page_stack = QStackedWidget()
        self._activity_bar = QWidget()

        self._chat_view = QTextEdit()
        self._chat_view.setReadOnly(True)

        self._plan_view = QTreeWidget()

        self._ida_view = QTreeWidget()

        self._workspace_view = QTreeWidget()

        self._dir_tree = DirectoryTreeWidget()
        self._hex_view = HexViewWidget()
        self._code_view = CodeViewWidget()
        self._dir_tree.file_selected.connect(self._on_file_selected)

        self._settings_view = SettingsPage(self.supervisor_client)
        self._settings_view.language_changed.connect(self._set_language)
        self._status_cards: dict[str, QWidget] = {}
        self._status_state_labels: dict[str, QLabel] = {}
        self._status_summary_labels: dict[str, QLabel] = {}
        self._status_detail_labels: dict[str, QLabel] = {}
        self._supervisor_menu = None
        self._gateway_worker: _GatewayWorker | None = None
        self._status_refresh_timer = QTimer(self)
        self._status_refresh_timer.timeout.connect(self.refresh_snapshot)

        self._build_shell()
        self.refresh_snapshot()

    def _t(self, key: str, **kwargs: object) -> str:
        return self._i18n.t(key, **kwargs)

    def _load_language(self) -> str:
        return normalize_language(self.supervisor_client.get_ide_config().language)

    def _build_shell(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_activity_bar())
        root_layout.addWidget(self._build_pages(), 1)

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self._build_actions()
        self._retranslate_ui()
        self._apply_mode("chat")
        self._apply_theme()

    def _build_activity_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("activityBar")
        bar.setFixedWidth(52)

        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 16, 0, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        icons = make_sidebar_icons(self._sidebar_icon_color())

        for mode, label_key in SIDEBAR_ITEMS:
            button = QToolButton()
            button.setObjectName("activityButton")
            button.setText("")
            button.setIcon(icons[mode])
            button.setIconSize(QSize(20, 20))
            button.setToolTip(self._t(label_key))
            button.setFixedSize(38, 38)
            button.setToolButtonStyle(Qt.ToolButtonIconOnly)
            button.clicked.connect(lambda checked, m=mode: self._apply_mode(m))
            layout.addWidget(button, alignment=Qt.AlignHCenter)
            self._activity_items[mode] = button

        self._activity_bar = bar
        self._set_active_activity("chat")
        return bar

    def _sidebar_icon_color(self) -> str:
        from app.ui.theme import ThemeMode

        return "#9ca3af" if self._current_theme_mode() == ThemeMode.LIGHT else "#6b7280"

    def _current_theme_mode(self):
        from app.ui.theme import ThemeMode

        return ThemeMode.LIGHT

    def _refresh_sidebar_icons(self) -> None:
        color = self._sidebar_icon_color()
        icons = make_sidebar_icons(color)
        for mode, button in self._activity_items.items():
            button.setIcon(icons[mode])

    def _build_pages(self) -> QWidget:
        self._page_stack.addWidget(self._build_chat_page())
        self._page_stack.addWidget(self._build_fs_page())
        self._page_stack.addWidget(self._build_settings_page())
        self._page_stack.addWidget(self._build_status_page())
        return self._page_stack

    def _build_chat_page(self) -> QWidget:
        left_split = QSplitter(Qt.Vertical)
        left_split.addWidget(
            self._build_panel("main.panel.plan", self._plan_view, "plan")
        )
        left_split.addWidget(
            self._build_panel("main.panel.ida_status", self._ida_view, "ida_status")
        )
        left_split.setSizes([380, 260])

        center = self._build_panel("main.panel.chat", self._chat_view, "chat")
        right = self._build_panel(
            "main.panel.workspace", self._workspace_view, "workspace"
        )

        main_split = QSplitter(Qt.Horizontal)
        main_split.addWidget(left_split)
        main_split.addWidget(center)
        main_split.addWidget(right)
        main_split.setSizes([320, 760, 340])
        return main_split

    def _build_fs_page(self) -> QWidget:
        # Stacked widget to switch between hex and code views
        self._file_view_stack = QStackedWidget()
        self._file_view_stack.addWidget(self._hex_view)
        self._file_view_stack.addWidget(self._code_view)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(
            self._build_panel("main.panel.workspace", self._dir_tree, "workspace_fs")
        )
        split.addWidget(self._build_panel("main.panel.fs", self._file_view_stack, "fs"))
        split.setSizes([280, 1140])
        return split

    def _on_file_selected(self, path: str) -> None:
        """Handle file selection from the directory tree.

        Strategy: try to open as text first. If UTF-8 decode fails or
        the file contains null bytes, fall back to hex view.
        """
        try:
            data = Path(path).read_bytes()
            # Heuristic: if the first 8KB contain a null byte, it's binary
            sample = data[:8192]
            if b"\x00" in sample:
                raise ValueError("binary file")
            text = data.decode("utf-8")
            self._code_view.load_file(path, text=text)
            self._file_view_stack.setCurrentIndex(1)
        except (UnicodeDecodeError, ValueError):
            self._hex_view.load_file(path)
            self._file_view_stack.setCurrentIndex(0)

    def _build_settings_page(self) -> QWidget:
        return self._settings_view

    def _build_status_page(self) -> QWidget:
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        refresh_button = QPushButton()
        refresh_button.clicked.connect(self.refresh_snapshot)
        toggle_button = QPushButton()
        toggle_button.setObjectName("primaryButton")
        toggle_button.clicked.connect(self._toggle_gateway)

        self._status_buttons = {
            "refresh": refresh_button,
            "toggle_gateway": toggle_button,
        }

        controls_layout.addWidget(refresh_button)
        controls_layout.addWidget(toggle_button)
        controls_layout.addStretch(1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        content_layout.addWidget(controls)
        content_layout.addWidget(self._build_status_cards(), 3)

        self._gateway_log = QTextEdit()
        self._gateway_log.setReadOnly(True)
        self._gateway_log.setMaximumHeight(160)
        content_layout.addWidget(self._gateway_log, 1)

        return self._build_panel("main.panel.status", content, "status")

    def _build_status_cards(self) -> QWidget:
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        for index, key in enumerate(
            ("supervisor", "gateway", "environment", "instances")
        ):
            card = self._create_status_card(key)
            layout.addWidget(card, index // 2, index % 2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        return widget

    def _create_status_card(self, key: str) -> QWidget:
        card = QFrame()
        card.setObjectName("statusCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title_label = QLabel()
        title_label.setObjectName("statusCardTitle")
        state_label = QLabel()
        state_label.setObjectName("statusState")
        summary_label = QLabel(self._t("main.status.waiting"))
        summary_label.setWordWrap(True)
        details_label = QLabel("")
        details_label.setWordWrap(True)
        details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(title_label)
        layout.addWidget(state_label)
        layout.addWidget(summary_label)
        layout.addWidget(details_label, 1)

        self._status_cards[key] = card
        self._status_card_titles[key] = title_label
        self._status_state_labels[key] = state_label
        self._status_summary_labels[key] = summary_label
        self._status_detail_labels[key] = details_label
        return card

    def _build_actions(self) -> None:
        refresh_action = QAction(self)
        refresh_action.triggered.connect(self.refresh_snapshot)

        start_gateway_action = QAction(self)
        start_gateway_action.triggered.connect(self._start_gateway)

        stop_gateway_action = QAction(self)

        stop_gateway_action.triggered.connect(self._stop_gateway)

        self._menu_actions = {
            "refresh_status": refresh_action,
            "start_gateway": start_gateway_action,
            "stop_gateway": stop_gateway_action,
        }

        self._supervisor_menu = None

    def _build_panel(self, title_key: str, widget: QWidget, panel_key: str) -> QWidget:
        container = QFrame()
        container.setObjectName("panel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel()
        title_label.setObjectName("panelTitle")
        title_label.setProperty("i18n_key", title_key)
        layout.addWidget(title_label)
        layout.addWidget(widget, 1)
        self._panel_labels[panel_key] = title_label
        return container

    def _set_active_activity(self, mode: str) -> None:
        for key, button in self._activity_items.items():
            button.setProperty("active", key == mode)
            button.style().unpolish(button)
            button.style().polish(button)

    def _apply_mode(self, mode: str) -> None:
        normalized = mode.strip().lower()
        self._set_active_activity(normalized)
        page_map = {"chat": 0, "fs": 1, "settings": 2, "status": 3}
        self._page_stack.setCurrentIndex(page_map.get(normalized, 0))
        label = self._t(dict(SIDEBAR_ITEMS).get(normalized, "sidebar.chat"))
        self.statusBar().showMessage(
            self._t("main.statusbar.switched", page=label),
            2000,
        )

    def _on_gateway_log(self, message: str) -> None:
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._gateway_log.append(f"[{timestamp}] {message}")

    def refresh_snapshot(self) -> None:
        if self._gateway_worker and self._gateway_worker.isRunning():
            return
        self._set_status_buttons_enabled(False)
        worker = _GatewayWorker("refresh", self.supervisor_client, parent=self)
        self._gateway_worker = worker
        worker.progress.connect(self._on_gateway_log)
        worker.finished.connect(self._on_snapshot_ready)
        worker.start()

    def _on_snapshot_ready(self, snapshot: object) -> None:
        self._set_status_buttons_enabled(True)
        from supervisor.models import SupervisorSnapshot

        if isinstance(snapshot, SupervisorSnapshot):
            self._snapshot = snapshot
            self._set_language(snapshot.config.language)
            self._render_snapshot(snapshot)
            self._update_toggle_button(snapshot)
            self.statusBar().showMessage(self._t("main.statusbar.refreshed"), 3000)

            if snapshot.gateway.alive:
                if not self._status_refresh_timer.isActive():
                    self._status_refresh_timer.start(10000)
            else:
                self._status_refresh_timer.stop()

    def _update_toggle_button(self, snapshot: SupervisorSnapshot) -> None:
        button = self._status_buttons.get("toggle_gateway")
        if button is None:
            return
        if snapshot.gateway.alive:
            button.setText(self._t("main.action.stop_gateway"))
            button.setProperty("gateway_running", True)
        else:
            button.setText(self._t("main.action.start_gateway"))
            button.setProperty("gateway_running", False)
        button.style().unpolish(button)
        button.style().polish(button)

    def _toggle_gateway(self) -> None:
        if self._gateway_worker and self._gateway_worker.isRunning():
            return
        if self._snapshot and self._snapshot.gateway.alive:
            self._stop_gateway()
        else:
            self._start_gateway()

    def _start_gateway(self) -> None:
        self._set_status_buttons_enabled(False)
        self.statusBar().showMessage(self._t("main.statusbar.starting"), 0)
        worker = _GatewayWorker("start", self.supervisor_client, parent=self)
        self._gateway_worker = worker
        worker.progress.connect(self._on_gateway_log)
        worker.finished.connect(self._on_snapshot_ready)
        worker.start()

    def _stop_gateway(self) -> None:
        reply = QMessageBox.question(
            self,
            self._t("main.dialog.stop_gateway.title"),
            self._t("main.dialog.stop_gateway.message"),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._set_status_buttons_enabled(False)
        self.statusBar().showMessage(self._t("main.statusbar.stopping"), 0)
        worker = _GatewayWorker("stop", self.supervisor_client, parent=self)
        self._gateway_worker = worker
        worker.progress.connect(self._on_gateway_log)
        worker.finished.connect(self._on_snapshot_ready)
        worker.start()

    def _render_snapshot(self, snapshot: SupervisorSnapshot) -> None:
        view_model = build_main_window_view_model(snapshot, self._t)
        self._update_status_cards(view_model)
        self._populate_tree(self._ida_view, view_model.ida_rows)
        self._populate_tree(self._workspace_view, view_model.workspace_rows)
        self._populate_tree(self._plan_view, view_model.plan_rows)

    def _update_status_cards(self, view_model: MainWindowViewModel) -> None:
        for card_view_model in view_model.status_cards:
            self._set_status_card(card_view_model)

    def _set_status_card(self, card_view_model: StatusCardViewModel) -> None:
        key = card_view_model.key
        state_label = self._status_state_labels[key]
        summary_label = self._status_summary_labels[key]
        details_label = self._status_detail_labels[key]

        self._status_card_titles[key].setText(card_view_model.title)
        state_label.setText(card_view_model.state_text)
        state_label.setProperty("state", card_view_model.state_property)
        summary_label.setText(card_view_model.summary)
        details_label.setText(card_view_model.details)
        card = self._status_cards[key]
        card.setProperty("state", card_view_model.state_property)
        state_label.style().unpolish(state_label)
        state_label.style().polish(state_label)
        card.style().unpolish(card)
        card.style().polish(card)

    def _set_status_buttons_enabled(self, enabled: bool) -> None:
        for button in self._status_buttons.values():
            button.setEnabled(enabled)

    def _populate_tree(self, tree: QTreeWidget, rows: list[TreeRowViewModel]) -> None:
        tree.clear()
        for row in rows:
            QTreeWidgetItem(tree, [row.label, row.value])

    def _set_language(self, language: str | None) -> None:
        normalized = normalize_language(language)
        if normalized == self._language:
            return
        self._language = normalized
        self._i18n.set_language(normalized)
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self._t("app.title"))
        self._chat_view.setPlainText(self._t("main.placeholder.chat"))
        self._plan_view.setHeaderLabels(
            [self._t("main.header.plan"), self._t("main.header.state")]
        )
        self._ida_view.setHeaderLabels(
            [self._t("main.header.ida"), self._t("main.header.value")]
        )
        self._workspace_view.setHeaderLabels(
            [self._t("main.header.workspace"), self._t("main.header.value")]
        )

        for mode, label_key in SIDEBAR_ITEMS:
            self._activity_items[mode].setToolTip(self._t(label_key))

        for label in self._panel_labels.values():
            label.setText(self._t(str(label.property("i18n_key"))))

        for key, label in self._status_card_titles.items():
            label.setText(self._t(STATUS_CARD_TITLE_KEYS[key]))

        if self._snapshot is None:
            for summary_label in self._status_summary_labels.values():
                summary_label.setText(self._t("main.status.waiting"))

        self._status_buttons["refresh"].setText(self._t("main.action.refresh_status"))
        # Toggle button text is set by _update_toggle_button based on gateway state
        if self._snapshot:
            self._update_toggle_button(self._snapshot)
        else:
            self._status_buttons["toggle_gateway"].setText(
                self._t("main.action.start_gateway")
            )

        self._menu_actions["refresh_status"].setText(
            self._t("main.action.refresh_status")
        )
        self._menu_actions["start_gateway"].setText(
            self._t("main.action.start_gateway")
        )
        self._menu_actions["stop_gateway"].setText(self._t("main.action.stop_gateway"))

        if self._snapshot is not None:
            self._render_snapshot(self._snapshot)

    def _apply_theme(self) -> None:
        self.setStyleSheet(Theme.light().stylesheet())
        self._refresh_sidebar_icons()
        self.refresh_snapshot()
