"""Settings page for the PySide6 IDE MVP."""

from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal

from shared.platform import display_path as _display_path
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import I18n, normalize_language
from app.presenters.settings_presenter import (
    SettingsFormState,
    build_check_message,
    build_reinstall_message,
    effective_install_python_path,
    form_state_to_updates,
    snapshot_to_form_state,
)
from app.services.settings_service import SettingsService


# ===================================================================
# Utility widgets
# ===================================================================

class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


# ===================================================================
# Model provider dialog
# ===================================================================

class ModelProviderDialog(QDialog):
    """Dialog for adding or editing a model provider entry."""

    def __init__(
        self,
        i18n,
        *,
        provider=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._provider = provider  # None = add new, else edit existing
        self._setup_ui()

    def _t(self, key: str, **kwargs: object) -> str:
        return self._i18n.t(key, **kwargs)

    def _setup_ui(self) -> None:
        self.setWindowTitle(
            self._t("settings.model.dialog.add")
            if self._provider is None
            else self._t("settings.model.dialog.edit")
        )
        self.setObjectName("modelProviderDialog")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(24, 24, 24, 24)

        # --- Section: Identity ---
        layout.addWidget(self._section_label(self._t("settings.field.model_name")))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("My GPT-4o")
        layout.addWidget(self._name_edit)

        layout.addSpacing(2)
        layout.addWidget(self._field_label(self._t("settings.field.model_id")))
        self._model_id_edit = QLineEdit()
        self._model_id_edit.setPlaceholderText("gpt-4o")
        layout.addWidget(self._model_id_edit)

        layout.addWidget(self._separator())
        layout.addSpacing(4)

        # --- Section: Connection ---
        layout.addWidget(self._section_label(self._t("settings.field.model_base_url")))
        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText("https://api.openai.com/v1")
        layout.addWidget(self._base_url_edit)

        layout.addSpacing(2)
        layout.addWidget(self._field_label(self._t("settings.field.model_api_key")))
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("sk-...")
        layout.addWidget(self._api_key_edit)

        layout.addSpacing(2)
        layout.addWidget(self._field_label(self._t("settings.field.model_api_mode")))
        self._api_mode_combo = NoWheelComboBox()
        self._api_mode_items = [
            ("openai_responses", self._t("settings.model.api_mode.openai_responses")),
            ("openai_compatible", self._t("settings.model.api_mode.openai_compatible")),
            ("anthropic", self._t("settings.model.api_mode.anthropic")),
            ("gemini", self._t("settings.model.api_mode.gemini")),
        ]
        for value, label in self._api_mode_items:
            self._api_mode_combo.addItem(label, value)
        self._api_mode_combo.setCurrentIndex(1)  # default: openai_compatible
        layout.addWidget(self._api_mode_combo)

        layout.addWidget(self._separator())
        layout.addSpacing(4)

        # --- Section: Parameters ---
        layout.addWidget(self._section_label(self._t("settings.field.model_top_p")))
        self._top_p_spin = NoWheelDoubleSpinBox()
        self._top_p_spin.setRange(0.0, 1.0)
        self._top_p_spin.setSingleStep(0.05)
        self._top_p_spin.setDecimals(2)
        self._top_p_spin.setValue(1.0)
        layout.addWidget(self._top_p_spin)

        layout.addSpacing(2)
        layout.addWidget(self._field_label(self._t("settings.field.model_temperature")))
        self._temp_spin = NoWheelDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.1)
        self._temp_spin.setDecimals(1)
        self._temp_spin.setValue(0.7)
        layout.addWidget(self._temp_spin)

        layout.addWidget(self._separator())
        layout.addSpacing(4)

        # --- Section: State ---
        layout.addWidget(self._field_label(self._t("settings.skills.enabled")))
        self._enabled_check = QCheckBox()
        self._enabled_check.setChecked(True)
        layout.addWidget(self._enabled_check)

        # Validation error label (hidden until needed)
        self._error_label = QLabel("")
        self._error_label.setObjectName("settingsErrorLabel")
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        layout.addWidget(self._error_label)

        layout.addSpacing(8)

        # Buttons
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._validate_and_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        # Pre-fill if editing
        if self._provider is not None:
            self._name_edit.setText(self._provider.name or "")
            self._base_url_edit.setText(self._provider.base_url or "")
            self._api_key_edit.setText(self._provider.api_key or "")
            self._model_id_edit.setText(self._provider.model_name or "")
            self._top_p_spin.setValue(self._provider.top_p)
            self._temp_spin.setValue(self._provider.temperature)
            self._enabled_check.setChecked(self._provider.enabled)
            # Set api_mode combo
            for i, (value, _) in enumerate(self._api_mode_items):
                if value == self._provider.api_mode:
                    self._api_mode_combo.setCurrentIndex(i)
                    break

    def get_values(self) -> dict:
        """Return a dict of all field values."""
        return {
            "name": self._name_edit.text().strip(),
            "base_url": self._base_url_edit.text().strip(),
            "api_key": self._api_key_edit.text().strip(),
            "api_mode": self._api_mode_combo.currentData() or "openai_compatible",
            "model_name": self._model_id_edit.text().strip(),
            "top_p": self._top_p_spin.value(),
            "temperature": self._temp_spin.value(),
            "enabled": self._enabled_check.isChecked(),
        }

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("dialogSectionTitle")
        return label

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("settingsFieldLabel")
        return label

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setObjectName("dialogSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        return line

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting the dialog."""
        errors: list[str] = []
        name = self._name_edit.text().strip()
        model_id = self._model_id_edit.text().strip()

        if not name:
            errors.append(self._t("settings.model.validation.name_required"))
        if not model_id:
            errors.append(self._t("settings.model.validation.model_id_required"))

        if errors:
            self._error_label.setText("\n".join(errors))
            self._error_label.show()
            return

        self._error_label.hide()
        self.accept()


# ===================================================================
# Background workers
# ===================================================================

class _InstallWorker(QThread):
    """Runs reinstall in a background thread."""
    progress = Signal(str)
    finished = Signal(object)  # InstallationActionResult

    def __init__(
        self,
        settings_service: SettingsService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._settings_service = settings_service

    def run(self) -> None:
        try:
            result = self._settings_service.reinstall(on_progress=self.progress.emit)
            self.finished.emit(result)
        except Exception as exc:
            self.progress.emit(f"Error: {exc}")
            self.finished.emit(None)


class _CheckWorker(QThread):
    """Runs installation check in a background thread."""
    finished = Signal(object)  # InstallationCheck

    def __init__(
        self,
        settings_service: SettingsService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._settings_service = settings_service

    def run(self) -> None:
        try:
            result = self._settings_service.check_installation()
            self.finished.emit(result)
        except Exception:
            self.finished.emit(None)


# ===================================================================
# ConfigFormBinder — data-driven field ↔ widget mapping
# ===================================================================

class _ConfigFormBinder:
    """Owns the field binding table and handles reading/writing form state."""

    _IDA_FIELD_BINDINGS: list[tuple[str, str, str]] = [
        ("enable_http", "_enable_http", "checkbox"),
        ("enable_stdio", "_enable_stdio", "checkbox"),
        ("enable_unsafe", "_enable_unsafe", "checkbox"),
        ("wsl_path_bridge", "_wsl_path_bridge", "checkbox"),
        ("http_host", "_http_host", "lineedit"),
        ("http_port", "_http_port", "spinbox"),
        ("http_path", "_http_path", "lineedit"),
        ("ida_default_port", "_ida_default_port", "spinbox"),
        ("ida_host", "_ida_host", "lineedit"),
        ("ida_path", "_ida_path", "lineedit"),
        ("ida_python", "_ida_python", "lineedit"),
        ("open_in_ida_bundle_dir", "_open_in_ida_bundle_dir", "lineedit"),
        ("open_in_ida_autonomous", "_open_in_ida_autonomous", "checkbox"),
        ("auto_start", "_auto_start", "checkbox"),
        ("server_name", "_server_name", "lineedit"),
        ("ida_request_timeout", "_ida_request_timeout", "spinbox"),
        ("debug", "_debug", "checkbox"),
    ]

    def __init__(self, page: SettingsPage) -> None:
        self._page = page

    def apply_form_state(self, form_state: SettingsFormState) -> None:
        """Populate widgets from a SettingsFormState."""
        for field_name, widget_attr, widget_type in self._IDA_FIELD_BINDINGS:
            widget = getattr(self._page, widget_attr)
            value = getattr(form_state, field_name)
            if widget_type == "checkbox":
                widget.setChecked(value)
            elif widget_type == "spinbox":
                widget.setValue(value)
            else:
                widget.setText(str(value))

    def collect_form_state(self, page: SettingsPage) -> SettingsFormState:
        """Read current widget values into a SettingsFormState."""
        data: dict[str, object] = {
            "plugin_dir": page._plugin_dir.text(),
            "language": str(page._language_combo.currentData() or page._language),
            "ide_request_timeout": page._ide_request_timeout.value(),
        }
        for field_name, widget_attr, widget_type in self._IDA_FIELD_BINDINGS:
            widget = getattr(page, widget_attr)
            if widget_type == "checkbox":
                data[field_name] = widget.isChecked()
            elif widget_type == "spinbox":
                data[field_name] = widget.value()
            else:
                data[field_name] = widget.text()
        return SettingsFormState.from_flat_dict(data)


# ===================================================================
# InstallationDisplay — requirements table and installation check UI
# ===================================================================

class _InstallationDisplay:
    """Renders installation check results into the requirements table."""

    def __init__(self, page: SettingsPage) -> None:
        self._page = page

    def _t(self, key: str, **kwargs: object) -> str:
        return self._page._t(key, **kwargs)

    def apply_installation_check(self, installation) -> None:
        """Render an InstallationCheck into the requirements widgets."""
        raw_path = installation.requirements_path or ""
        display = _display_path(raw_path) if raw_path else ""
        self._page._requirements_path.setText(
            display or self._t("settings.install.requirements.missing")
        )
        self._page._requirements_table.setHorizontalHeaderLabels(
            [
                self._t("settings.install.table.package"),
                self._t("settings.install.table.required"),
                self._t("settings.install.table.installed"),
            ]
        )
        rows = self._build_requirement_rows(installation)
        self._page._requirements_table.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            for column_index, value in enumerate(row_values):
                self._page._requirements_table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(value),
                )

    def _build_requirement_rows(self, installation) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        installed = installation.installed_requirements
        missing = set(installation.missing_requirements)
        unresolved = set(installation.unresolved_requirements)
        for requirement in installation.requirements:
            if requirement in installed:
                status = (
                    f"{self._t('settings.install.table.status.installed')} "
                    f"({installed[requirement]})"
                )
            elif requirement in missing:
                status = self._t("settings.install.table.status.missing")
            elif requirement in unresolved:
                status = self._t("settings.install.table.status.unresolved")
            else:
                status = self._t("settings.install.table.status.unresolved")
            rows.append(
                (self._requirement_package_name(requirement), requirement, status)
            )
        return rows

    @staticmethod
    def _requirement_package_name(requirement: str) -> str:
        for index, char in enumerate(requirement):
            if not (char.isalnum() or char in "._-"):
                return requirement[:index]
        return requirement


# ===================================================================
# InstallController — background worker lifecycle for install/check
# ===================================================================

class _InstallController:
    """Manages background worker threads for installation and checking.

    All worker creation/teardown is encapsulated here.  The host page
    receives results through callback callables.
    """

    def __init__(
        self,
        page: SettingsPage,
        settings_service: SettingsService,
        *,
        on_check_result,       # callable(InstallationCheck)
        on_install_result,     # callable(InstallationActionResult)
        on_progress,           # callable(str)
        on_busy_changed,       # callable(bool)
    ) -> None:
        self._page = page
        self._settings_service = settings_service
        self._on_check_result = on_check_result
        self._on_install_result = on_install_result
        self._on_progress = on_progress
        self._on_busy_changed = on_busy_changed
        self._install_worker: _InstallWorker | None = None
        self._check_worker: _CheckWorker | None = None

    @property
    def is_install_busy(self) -> bool:
        return self._install_worker is not None and self._install_worker.isRunning()

    def run_check(self) -> None:
        """Start a background installation check."""
        self._cleanup_check_worker()
        worker = _CheckWorker(self._settings_service, parent=self._page)
        self._check_worker = worker
        worker.finished.connect(
            lambda result, w=worker: self._on_check_finished(result, w)
        )
        worker.start()

    def run_install(self) -> None:
        """Start a background reinstall."""
        if self.is_install_busy:
            return
        self._cleanup_install_worker()
        self._on_busy_changed(False)
        worker = _InstallWorker(self._settings_service, parent=self._page)
        self._install_worker = worker
        worker.progress.connect(self._on_progress)
        worker.finished.connect(
            lambda result, w=worker: self._on_install_finished(result, w)
        )
        worker.start()

    def _on_check_finished(self, result: object, worker: _CheckWorker) -> None:
        if self._check_worker is not worker:
            # Stale worker — discard the result to avoid overwriting newer state.
            worker.deleteLater()
            return
        worker.deleteLater()
        self._check_worker = None
        if result is not None:
            self._on_check_result(result)

    def _on_install_finished(self, result: object, worker: _InstallWorker) -> None:
        if self._install_worker is worker:
            worker.deleteLater()
            self._install_worker = None
            self._on_busy_changed(True)
        from supervisor.models import InstallationActionResult

        if not isinstance(result, InstallationActionResult):
            self._on_progress("Error: Unexpected result type")
            return
        self._on_install_result(result)

    def _cleanup_install_worker(self) -> None:
        worker = self._install_worker
        if worker is None:
            return
        if worker.isRunning():
            worker.quit()
            worker.wait(3000)
        worker.deleteLater()
        self._install_worker = None

    def _cleanup_check_worker(self) -> None:
        worker = self._check_worker
        if worker is None:
            return
        if worker.isRunning():
            worker.quit()
            worker.wait(3000)
        worker.deleteLater()
        self._check_worker = None


# ===================================================================
# SettingsPage — thin orchestrator
# ===================================================================

class SettingsPage(QWidget):
    language_changed = Signal(str)

    def __init__(
        self,
        settings_service: SettingsService | None = None,
    ) -> None:
        super().__init__()
        self._settings_service = settings_service or SettingsService()

        initial_snapshot = self._settings_service.load()
        self._language = normalize_language(initial_snapshot.ide_config.language)
        self._i18n = I18n(self._language)

        self._title_label = QLabel()
        self._title_label.setObjectName("settingsTitle")
        self._category_list = QListWidget()
        self._stack = QStackedWidget()
        self._category_row_connected = False
        self._language_combo_connected = False
        self._retained_widgets: list[QWidget] = []

        self._install_notes = QTextEdit()
        self._install_notes.setReadOnly(True)
        self._requirements_path = QLineEdit()
        self._requirements_path.setReadOnly(True)
        self._requirements_table = QTableWidget(0, 3)
        self._requirements_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._requirements_table.setSelectionMode(QTableWidget.NoSelection)
        self._requirements_table.verticalHeader().setVisible(False)
        self._requirements_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self._requirements_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self._requirements_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self._upgrade_notes = QTextEdit()
        self._upgrade_notes.setReadOnly(True)
        self._save_hint_label = QLabel()
        self._save_hint_label.setObjectName("settingsHint")

        self._install_python_path = QLineEdit()
        self._install_python_path.setReadOnly(True)
        self._install_plugin_dir = QLineEdit()
        self._install_plugin_dir.setReadOnly(True)

        self._plugin_dir = QLineEdit()
        self._language_combo = NoWheelComboBox()
        self._ide_request_timeout = NoWheelSpinBox()
        self._ide_request_timeout.setRange(1, 3600)
        self._ide_request_timeout.setSuffix(" s")

        self._enable_http = QCheckBox()
        self._enable_stdio = QCheckBox()
        self._enable_unsafe = QCheckBox()
        self._wsl_path_bridge = QCheckBox()
        self._http_host = QLineEdit()
        self._http_port = NoWheelSpinBox()
        self._http_port.setRange(1, 65535)
        self._http_path = QLineEdit()
        self._ida_default_port = NoWheelSpinBox()
        self._ida_default_port.setRange(1, 65535)
        self._ida_host = QLineEdit()
        self._ida_path = QLineEdit()
        self._ida_python = QLineEdit()
        self._open_in_ida_bundle_dir = QLineEdit()
        self._open_in_ida_bundle_dir_field = self._path_field(
            self._open_in_ida_bundle_dir,
            self._browse_directory,
        )
        self._open_in_ida_autonomous = QCheckBox()
        self._auto_start = QCheckBox()
        self._server_name = QLineEdit()
        self._ida_request_timeout = NoWheelSpinBox()
        self._ida_request_timeout.setRange(1, 3600)
        self._ida_request_timeout.setSuffix(" s")
        self._debug = QCheckBox()
        self._advanced_container = QWidget()

        # --- Model providers widgets ---
        self._model_providers_table = QTableWidget(0, 6)
        self._model_providers_table.setObjectName("modelProvidersTable")
        self._model_providers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._model_providers_table.setSelectionMode(QTableWidget.NoSelection)
        self._model_providers_table.verticalHeader().setVisible(False)
        self._model_providers_table.setAlternatingRowColors(True)
        self._model_providers_table.setShowGrid(False)
        self._model_providers_table.verticalHeader().setDefaultSectionSize(38)
        self._model_providers_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self._model_providers_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self._model_providers_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self._model_providers_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self._model_providers_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeToContents
        )
        self._model_providers_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeToContents
        )

        # --- MCP settings widgets ---
        self._mcp_servers_table = QTableWidget(0, 2)
        self._mcp_servers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._mcp_servers_table.setSelectionMode(QTableWidget.SingleSelection)
        self._mcp_servers_table.verticalHeader().setVisible(False)
        self._mcp_servers_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._mcp_servers_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )

        # --- Skills table ---
        self._skills_table = QTableWidget(0, 3)
        self._skills_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._skills_table.setSelectionMode(QTableWidget.NoSelection)
        self._skills_table.verticalHeader().setVisible(False)
        self._skills_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self._skills_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self._skills_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )

        self._advanced_layout = QVBoxLayout(self._advanced_container)
        self._advanced_layout.setContentsMargins(0, 0, 0, 0)
        self._advanced_layout.setSpacing(12)
        self._advanced_toggle = QToolButton()
        self._advanced_toggle.setCheckable(True)
        self._advanced_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._advanced_toggle.clicked.connect(self._toggle_other_options)
        self._wsl_toggle = QToolButton()
        self._wsl_toggle.setCheckable(True)
        self._wsl_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._wsl_toggle.clicked.connect(self._toggle_wsl_section)
        self._wsl_container = QWidget()
        self._wsl_layout = QVBoxLayout(self._wsl_container)
        self._wsl_layout.setContentsMargins(0, 0, 0, 0)
        self._wsl_layout.setSpacing(12)
        self._wsl_path_bridge.toggled.connect(self._sync_wsl_bridge_fields)
        self._advanced_runtime_group: QWidget | None = None
        self._wsl_group: QWidget | None = None

        # --- Delegated helpers ---
        self._form_binder = _ConfigFormBinder(self)
        self._install_display = _InstallationDisplay(self)
        self._install_ctrl = _InstallController(
            self,
            self._settings_service,
            on_check_result=self._install_display.apply_installation_check,
            on_install_result=self._handle_install_result,
            on_progress=self._on_install_progress,
            on_busy_changed=self._set_install_buttons_enabled,
        )

        self._build_ui()
        self._apply_snapshot(initial_snapshot)

    def _t(self, key: str, **kwargs: object) -> str:
        return self._i18n.t(key, **kwargs)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        current_row = self._category_list.currentRow()
        old_layout = self.layout()
        if old_layout is None:
            root_layout = QVBoxLayout(self)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.setSpacing(10)

            header = QWidget()
            header_layout = QVBoxLayout(header)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(6)
            header_layout.addWidget(self._title_label)

            body = QWidget()
            body_layout = QHBoxLayout(body)
            body_layout.setContentsMargins(0, 0, 0, 0)
            body_layout.setSpacing(12)
            body_layout.addWidget(self._category_list)
            body_layout.addWidget(self._stack, 1)

            root_layout.addWidget(header)
            root_layout.addWidget(body, 1)

        self._title_label.setText(self._t("settings.title"))

        self._category_list.clear()
        self._category_list.setObjectName("settingsCategoryList")
        self._category_list.setFixedWidth(180)
        for name in (
            self._t("settings.category.config"),
            self._t("settings.category.install"),
            self._t("settings.category.upgrade"),
            self._t("settings.category.model"),
            self._t("settings.category.mcp_settings"),
            self._t("settings.category.skills"),
        ):
            item = QListWidgetItem(name)
            font = item.font()
            if font.pointSize() <= 0:
                ps = self.font().pointSize()
                font.setPointSize(ps if ps > 0 else 10)
            font.setBold(True)
            item.setFont(font)
            self._category_list.addItem(item)
        if not self._category_row_connected:
            self._category_list.currentRowChanged.connect(self._stack.setCurrentIndex)
            self._category_row_connected = True

        while self._stack.count():
            page = self._stack.widget(0)
            self._stack.removeWidget(page)
            page.setParent(None)
            self._retained_widgets.append(page)

        self._stack.addWidget(self._build_config_page())
        self._stack.addWidget(self._build_install_page())
        self._stack.addWidget(self._build_upgrade_page())
        self._stack.addWidget(self._build_model_page())
        self._stack.addWidget(self._build_mcp_settings_page())
        self._stack.addWidget(self._build_skills_page())

        if current_row < 0:
            current_row = 0
        self._category_list.setCurrentRow(current_row)

    def _build_config_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(
            self._build_config_group(
                self._t("settings.group.global_paths"),
                self._t("settings.group.global_paths.desc"),
                [
                    self._build_field_row(
                        self._t("settings.field.plugin_dir"),
                        self._t("settings.field.plugin_dir.desc"),
                        self._path_field(self._plugin_dir, self._browse_directory),
                    ),
                ],
            )
        )
        layout.addWidget(
            self._build_config_group(
                self._t("settings.group.runtime"),
                self._t("settings.group.runtime.desc"),
                [
                    self._build_field_row(
                        self._t("settings.field.language"),
                        self._t("settings.field.language.desc"),
                        self._build_language_field(),
                    ),
                    self._build_field_row(
                        self._t("settings.field.ide_request_timeout"),
                        self._t("settings.field.ide_request_timeout.desc"),
                        self._ide_request_timeout,
                    ),
                ],
            )
        )
        layout.addWidget(
            self._build_config_group(
                self._t("settings.group.transport"),
                self._t("settings.group.transport.desc"),
                [
                    self._build_checkbox_row(
                        self._enable_http,
                        self._t("settings.field.enable_http"),
                        self._t("settings.field.enable_http.desc"),
                    ),
                    self._build_checkbox_row(
                        self._enable_stdio,
                        self._t("settings.field.enable_stdio"),
                        self._t("settings.field.enable_stdio.desc"),
                    ),
                    self._build_checkbox_row(
                        self._enable_unsafe,
                        self._t("settings.field.enable_unsafe"),
                        self._t("settings.field.enable_unsafe.desc"),
                    ),
                    self._build_field_row(
                        self._t("settings.field.http_host"),
                        self._t("settings.field.http_host.desc"),
                        self._http_host,
                    ),
                    self._build_field_row(
                        self._t("settings.field.http_port"),
                        self._t("settings.field.http_port.desc"),
                        self._http_port,
                    ),
                    self._build_field_row(
                        self._t("settings.field.http_path"),
                        self._t("settings.field.http_path.desc"),
                        self._http_path,
                    ),
                    self._build_checkbox_row(
                        self._debug,
                        self._t("settings.field.debug"),
                        self._t("settings.field.debug.desc"),
                    ),
                ],
            )
        )
        layout.addWidget(
            self._build_config_group(
                self._t("settings.group.execution"),
                self._t("settings.group.execution.desc"),
                [
                    self._build_field_row(
                        self._t("settings.field.ida_executable"),
                        self._t("settings.field.ida_executable.desc"),
                        self._path_field(self._ida_path, self._browse_file),
                    ),
                    self._build_field_row(
                        self._t("settings.field.ida_python"),
                        self._t("settings.field.ida_python_effective.desc"),
                        self._path_field(self._ida_python, self._browse_file),
                    ),
                    self._build_field_row(
                        self._t("settings.field.ida_default_port"),
                        self._t("settings.field.ida_default_port.desc"),
                        self._ida_default_port,
                    ),
                    self._build_field_row(
                        self._t("settings.field.ida_host"),
                        self._t("settings.field.ida_host.desc"),
                        self._ida_host,
                    ),
                    self._build_field_row(
                        self._t("settings.field.ida_request_timeout"),
                        self._t("settings.field.ida_request_timeout.desc"),
                        self._ida_request_timeout,
                    ),
                    self._build_checkbox_row(
                        self._open_in_ida_autonomous,
                        self._t("settings.field.open_in_ida_autonomous"),
                        self._t("settings.field.open_in_ida_autonomous.desc"),
                    ),
                    self._build_checkbox_row(
                        self._auto_start,
                        self._t("settings.field.auto_start"),
                        self._t("settings.field.auto_start.desc"),
                    ),
                    self._build_field_row(
                        self._t("settings.field.server_name"),
                        self._t("settings.field.server_name.desc"),
                        self._server_name,
                    ),
                ],
            )
        )

        self._refresh_advanced_section()
        self._refresh_wsl_section()
        layout.addWidget(self._wsl_toggle)
        layout.addWidget(self._wsl_container)
        layout.addWidget(self._advanced_toggle)
        layout.addWidget(self._advanced_container)

        layout.addStretch(1)

        layout.addWidget(self._build_save_bar(show_hint=True))

        return self._wrap_scroll(widget)

    def _build_install_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(
            self._build_config_group(
                self._t("settings.install.inputs"),
                self._t("settings.install.inputs.desc"),
                [
                    self._build_field_row(
                        self._t("settings.field.ida_python"),
                        self._t("settings.field.ida_python_effective.desc"),
                        self._install_python_path,
                    ),
                    self._build_field_row(
                        self._t("settings.field.plugin_dir"),
                        self._t("settings.field.plugin_dir.desc"),
                        self._install_plugin_dir,
                    ),
                ],
            )
        )
        layout.addWidget(
            self._build_config_group(
                self._t("settings.install.requirements"),
                self._t("settings.install.requirements.desc"),
                [
                    self._build_field_row(
                        self._t("settings.install.requirements_path"),
                        self._t("settings.install.requirements_path.desc"),
                        self._requirements_path,
                    ),
                    self._requirements_table,
                ],
            )
        )
        layout.addWidget(self._install_notes)

        action_bar = QWidget()
        action_bar_layout = QHBoxLayout(action_bar)
        action_bar_layout.setContentsMargins(0, 0, 0, 0)
        action_bar_layout.setSpacing(8)
        check_button = QPushButton(self._t("settings.install.check"))
        check_button.clicked.connect(self.check)
        install_button = QPushButton(self._t("settings.install.install"))
        install_button.setObjectName("primaryButton")
        install_button.clicked.connect(self.reinstall)
        action_bar_layout.addStretch(1)
        action_bar_layout.addWidget(check_button)
        action_bar_layout.addWidget(install_button)
        layout.addWidget(action_bar)

        layout.addStretch(1)
        return self._wrap_scroll(widget)

    def _build_upgrade_page(self) -> QWidget:
        self._upgrade_notes.setPlainText(self._t("settings.upgrade.placeholder"))
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._upgrade_notes)
        layout.addStretch(1)
        return widget

    # ------------------------------------------------------------------
    # Model providers page
    # ------------------------------------------------------------------

    def _build_model_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._model_providers_table.setHorizontalHeaderLabels(
            [
                self._t("settings.field.model_name"),
                self._t("settings.field.model_base_url"),
                self._t("settings.field.model_id"),
                self._t("settings.field.model_api_mode"),
                self._t("settings.skills.enabled"),
                "",
            ]
        )

        layout.addWidget(
            self._build_config_group(
                self._t("settings.group.model_providers"),
                self._t("settings.group.model_providers.desc"),
                [self._model_providers_table],
            )
        )

        self._model_providers_table.cellDoubleClicked.connect(self._edit_model_provider)

        action_bar = QWidget()
        action_bar_layout = QHBoxLayout(action_bar)
        action_bar_layout.setContentsMargins(0, 0, 0, 0)
        action_bar_layout.setSpacing(8)
        add_button = QPushButton(self._t("settings.model.add"))
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._add_model_provider)
        action_bar_layout.addWidget(add_button)
        action_bar_layout.addStretch(1)
        layout.addWidget(action_bar)

        layout.addStretch(1)
        layout.addWidget(self._build_save_bar(show_hint=True))
        return self._wrap_scroll(widget)

    def _add_model_provider(self) -> None:
        dialog = ModelProviderDialog(self._i18n, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.get_values()
        self._settings_service.add_model_provider(**values)
        self._refresh_model_providers_table()

    def _edit_model_provider(self, row: int, _col: int) -> None:
        item = self._model_providers_table.item(row, 0)
        if item is None:
            return
        provider_id = item.data(Qt.ItemDataRole.UserRole)
        if provider_id is None:
            return
        providers = self._settings_service.get_model_providers()
        provider = next((p for p in providers if p.id == provider_id), None)
        if provider is None:
            return
        dialog = ModelProviderDialog(self._i18n, provider=provider, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.get_values()
        self._settings_service.update_model_provider(provider_id, **values)
        self._refresh_model_providers_table()

    def _delete_model_provider(self, provider_id: int) -> None:
        self._settings_service.remove_model_provider(provider_id)
        self._refresh_model_providers_table()

    def _refresh_model_providers_table(self) -> None:
        from PySide6.QtGui import QColor

        api_mode_labels = {
            "openai_responses": self._t("settings.model.api_mode.openai_responses"),
            "openai_compatible": self._t("settings.model.api_mode.openai_compatible"),
            "anthropic": self._t("settings.model.api_mode.anthropic"),
            "gemini": self._t("settings.model.api_mode.gemini"),
        }

        enabled_text = self._t("settings.bool.yes")
        disabled_text = self._t("settings.bool.no")

        providers = self._settings_service.get_model_providers()
        self._model_providers_table.setRowCount(len(providers))
        for row_index, provider in enumerate(providers):
            # Name (bold)
            name_item = QTableWidgetItem(provider.name or "")
            name_item.setData(Qt.ItemDataRole.UserRole, provider.id)
            name_font = name_item.font()
            name_font.setBold(True)
            name_item.setFont(name_font)
            self._model_providers_table.setItem(row_index, 0, name_item)

            self._model_providers_table.setItem(
                row_index, 1, QTableWidgetItem(provider.base_url or "")
            )
            self._model_providers_table.setItem(
                row_index, 2, QTableWidgetItem(provider.model_name or "")
            )
            self._model_providers_table.setItem(
                row_index, 3,
                QTableWidgetItem(api_mode_labels.get(provider.api_mode, provider.api_mode)),
            )

            # Enabled indicator (green ● or gray ●)
            is_enabled = bool(provider.enabled)
            dot = "●  " + (enabled_text if is_enabled else disabled_text)
            enabled_item = QTableWidgetItem(dot)
            enabled_item.setForeground(
                QColor("#059669") if is_enabled else QColor("#9ca3af")
            )
            self._model_providers_table.setItem(row_index, 4, enabled_item)

            # Per-row delete button (flat danger style)
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            del_btn = QPushButton(self._t("settings.model.remove"))
            del_btn.setObjectName("dangerButton")
            del_btn.setFixedHeight(26)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(
                lambda checked, pid=provider.id: self._delete_model_provider(pid)
            )
            btn_layout.addWidget(del_btn)
            self._model_providers_table.setCellWidget(row_index, 5, btn_widget)

    # ------------------------------------------------------------------
    # MCP settings page
    # ------------------------------------------------------------------

    def _build_mcp_settings_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._mcp_servers_table.setHorizontalHeaderLabels(
            [
                self._t("settings.field.mcp_server_name"),
                self._t("settings.field.mcp_server_url"),
            ]
        )

        layout.addWidget(
            self._build_config_group(
                self._t("settings.group.mcp_servers"),
                self._t("settings.group.mcp_servers.desc"),
                [self._mcp_servers_table],
            )
        )

        action_bar = QWidget()
        action_bar_layout = QHBoxLayout(action_bar)
        action_bar_layout.setContentsMargins(0, 0, 0, 0)
        action_bar_layout.setSpacing(8)
        add_button = QPushButton(self._t("settings.mcp.add"))
        remove_button = QPushButton(self._t("settings.mcp.remove"))
        action_bar_layout.addWidget(add_button)
        action_bar_layout.addWidget(remove_button)
        action_bar_layout.addStretch(1)
        layout.addWidget(action_bar)

        layout.addStretch(1)
        layout.addWidget(self._build_save_bar(show_hint=True))
        return self._wrap_scroll(widget)

    # ------------------------------------------------------------------
    # Skills settings page
    # ------------------------------------------------------------------

    def _build_skills_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._skills_table.setHorizontalHeaderLabels(
            [
                self._t("settings.skills.enabled"),
                self._t("settings.skills.name"),
                self._t("settings.skills.description"),
            ]
        )

        layout.addWidget(
            self._build_config_group(
                self._t("settings.group.skills_registry"),
                self._t("settings.group.skills_registry.desc"),
                [self._skills_table],
            )
        )

        layout.addStretch(1)
        return self._wrap_scroll(widget)

    # ------------------------------------------------------------------
    # Snapshot / state application
    # ------------------------------------------------------------------

    def reload(self) -> None:
        self._apply_snapshot(self._settings_service.load())

    def _apply_snapshot(self, snapshot) -> None:
        previous_language = self._language
        self._language = normalize_language(snapshot.ide_config.language)
        self._i18n.set_language(self._language)
        self._refresh_language_combo()

        form_state = snapshot_to_form_state(snapshot)
        self._plugin_dir.setText(form_state.plugin_dir)
        self._ide_request_timeout.setValue(form_state.ide_request_timeout)
        self._install_python_path.setText(effective_install_python_path(snapshot))
        self._install_plugin_dir.setText(form_state.plugin_dir)
        self._save_hint_label.setText(self._t("settings.save_hint"))
        self._install_notes.setPlaceholderText(self._t("settings.install.placeholder"))

        # Defer installation check to a background worker — never block UI.
        self._install_ctrl.run_check()

        self._form_binder.apply_form_state(form_state)

        self._sync_wsl_bridge_fields()
        if self._language != previous_language:
            self.language_changed.emit(self._language)

    # ------------------------------------------------------------------
    # Save / check / install
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Stop background workers. Call before the page is destroyed."""
        self._install_ctrl._cleanup_check_worker()
        self._install_ctrl._cleanup_install_worker()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.cleanup()
        super().closeEvent(event)

    def save(self) -> None:
        self._save_settings(show_message=True)

    def _save_settings(self, *, show_message: bool) -> None:
        form_state = self._form_binder.collect_form_state(self)
        ide_updates, ida_mcp_updates = form_state_to_updates(form_state)
        snapshot = self._settings_service.save(
            ide_updates=ide_updates,
            ida_mcp_updates=ida_mcp_updates,
        )
        self._apply_snapshot(snapshot)
        self._save_hint_label.setText(self._t("settings.saved"))
        if show_message:
            QMessageBox.information(
                self,
                self._t("settings.dialog.settings"),
                self._t("settings.saved.message"),
            )

    def check(self) -> None:
        self._save_settings(show_message=False)
        # The save above triggers _apply_snapshot which fires a background
        # check.  We also run a synchronous check here for the dialog message,
        # matching the original behaviour for the "Check" button.
        installation = self._settings_service.check_installation()
        self._install_display.apply_installation_check(installation)
        report = self._settings_service.check()
        message = build_check_message(report, installation, self._t, self._bool_text)
        self._install_notes.setPlainText(message.details)
        QMessageBox.information(
            self,
            self._t("settings.dialog.check"),
            message.details,
        )

    def reinstall(self) -> None:
        self._save_settings(show_message=False)
        self._set_install_buttons_enabled(False)
        self._install_notes.setPlainText("")
        self._install_notes.append(self._t("settings.install.starting"))
        self._install_ctrl.run_install()

    def _on_install_progress(self, message: str) -> None:
        self._install_notes.append(message)

    def _handle_install_result(self, result) -> None:
        self._install_display.apply_installation_check(result.check)
        message = build_reinstall_message(result, self._t, self._bool_text)
        QMessageBox.information(
            self,
            self._t("settings.dialog.install"),
            message.details,
        )

    def _set_install_buttons_enabled(self, enabled: bool) -> None:
        page = self._stack.widget(1)  # install page
        if page is None:
            return
        for button in page.findChildren(QPushButton):
            button.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Reusable widget builders
    # ------------------------------------------------------------------

    def _build_config_group(
        self,
        title: str,
        description: str,
        rows: list[QWidget],
    ) -> QWidget:
        container = QFrame()
        container.setObjectName("settingsGroup")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("settingsGroupTitle")
        description_label = QLabel(description)
        description_label.setObjectName("settingsGroupDescription")
        description_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        for row in rows:
            layout.addWidget(row)
        return container

    def _build_save_bar(self, *, show_hint: bool) -> QWidget:
        save_bar = QWidget()
        save_bar_layout = QHBoxLayout(save_bar)
        save_bar_layout.setContentsMargins(0, 0, 0, 0)
        save_bar_layout.setSpacing(8)
        if show_hint:
            self._save_hint_label.setText(self._t("settings.save_hint"))
            save_bar_layout.addWidget(self._save_hint_label, 1)
        else:
            save_bar_layout.addStretch(1)
        save_button = QPushButton(self._t("settings.save"))
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save)
        reload_button = QPushButton(self._t("settings.reload"))
        reload_button.clicked.connect(self.reload)
        save_bar_layout.addWidget(reload_button)
        save_bar_layout.addWidget(save_button)
        return save_bar

    def _build_field_row(self, label: str, description: str, field: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label_widget = QLabel(label)
        label_widget.setObjectName("settingsFieldLabel")
        description_widget = QLabel(description)
        description_widget.setWordWrap(True)
        description_widget.setObjectName("settingsFieldDescription")

        layout.addWidget(label_widget)
        layout.addWidget(description_widget)
        layout.addWidget(field)
        return container

    def _build_checkbox_row(
        self,
        checkbox: QCheckBox,
        label: str,
        description: str,
    ) -> QWidget:
        checkbox.setText(label)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        description_widget = QLabel(description)
        description_widget.setWordWrap(True)
        description_widget.setObjectName("settingsFieldDescription")

        layout.addWidget(checkbox)
        layout.addWidget(description_widget)
        return container

    def _build_language_field(self) -> QWidget:
        self._refresh_language_combo()
        return self._language_combo

    def _refresh_language_combo(self) -> None:
        self._language_combo.blockSignals(True)
        self._language_combo.clear()
        self._language_combo.addItem(self._t("settings.language.english"), "en")
        self._language_combo.addItem(self._t("settings.language.chinese"), "zh")
        self._language_combo.setCurrentIndex(0 if self._language == "en" else 1)
        if not self._language_combo_connected:
            self._language_combo.currentIndexChanged.connect(self._on_language_changed)
            self._language_combo_connected = True
        self._language_combo.blockSignals(False)

    def _on_language_changed(self) -> None:
        language = normalize_language(self._language_combo.currentData())
        if language == self._language:
            return
        self._language = language
        self._i18n.set_language(language)
        self._build_ui()
        self._save_hint_label.setText(self._t("settings.save_hint"))
        self._install_notes.setPlaceholderText(self._t("settings.install.placeholder"))
        self.language_changed.emit(language)

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        return scroll

    def _path_field(self, widget: QLineEdit, picker) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        button = QPushButton(self._t("settings.button.browse"))
        button.clicked.connect(lambda: picker(widget))
        layout.addWidget(widget, 1)
        layout.addWidget(button)
        return container

    def _browse_file(self, widget: QLineEdit) -> None:
        start = widget.text().strip() or ""
        selected, _ = QFileDialog.getOpenFileName(
            self,
            self._t("settings.dialog.select_file"),
            start,
        )
        if selected:
            widget.setText(selected)

    def _browse_directory(self, widget: QLineEdit) -> None:
        start = widget.text().strip() or ""
        selected = QFileDialog.getExistingDirectory(
            self,
            self._t("settings.dialog.select_directory"),
            start,
        )
        if selected:
            widget.setText(selected)

    def _bool_text(self, value: bool) -> str:
        return self._t("settings.bool.yes") if value else self._t("settings.bool.no")

    # ------------------------------------------------------------------
    # WSL / advanced section toggles
    # ------------------------------------------------------------------

    def _toggle_other_options(self) -> None:
        self._refresh_advanced_section()

    def _toggle_wsl_section(self) -> None:
        self._refresh_wsl_section()

    def _sync_wsl_bridge_fields(self) -> None:
        enabled = self._wsl_path_bridge.isChecked()
        if not enabled:
            self._open_in_ida_bundle_dir.clear()
        self._open_in_ida_bundle_dir_field.setEnabled(enabled)

    def _refresh_wsl_section(self) -> None:
        show_wsl = self._wsl_toggle.isChecked()
        self._wsl_toggle.setText(self._t("settings.group.wsl"))
        self._wsl_toggle.setArrowType(Qt.DownArrow if show_wsl else Qt.RightArrow)
        self._wsl_toggle.blockSignals(True)
        self._wsl_toggle.setChecked(show_wsl)
        self._wsl_toggle.blockSignals(False)
        self._wsl_container.setVisible(show_wsl)

        if self._wsl_group is not None:
            self._wsl_layout.removeWidget(self._wsl_group)
            self._wsl_group.setParent(None)
            self._retained_widgets.append(self._wsl_group)
            self._wsl_group = None

        if not show_wsl:
            return

        self._wsl_group = self._build_config_group(
            self._t("settings.group.wsl"),
            self._t("settings.group.wsl.desc"),
            [
                self._build_checkbox_row(
                    self._wsl_path_bridge,
                    self._t("settings.field.wsl_path_bridge"),
                    self._t("settings.field.wsl_path_bridge.desc"),
                ),
                self._build_field_row(
                    self._t("settings.field.open_in_ida_bundle_dir"),
                    self._t("settings.field.open_in_ida_bundle_dir.desc"),
                    self._open_in_ida_bundle_dir_field,
                ),
            ],
        )
        self._wsl_layout.addWidget(self._wsl_group)

    def _refresh_advanced_section(self) -> None:
        show_other_options = self._advanced_toggle.isChecked()
        self._advanced_toggle.setText(
            self._t("settings.button.hide_other_options")
            if show_other_options
            else self._t("settings.button.show_other_options")
        )
        self._advanced_toggle.setArrowType(
            Qt.DownArrow if show_other_options else Qt.RightArrow
        )
        self._advanced_toggle.blockSignals(True)
        self._advanced_toggle.setChecked(show_other_options)
        self._advanced_toggle.blockSignals(False)
        self._advanced_container.setVisible(show_other_options)
        for group_attr in ("_advanced_runtime_group",):
            group = getattr(self, group_attr)
            if group is not None:
                self._advanced_layout.removeWidget(group)
                group.setParent(None)
                self._retained_widgets.append(group)
                setattr(self, group_attr, None)

        if not show_other_options:
            return
