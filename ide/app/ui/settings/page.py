"""Settings page for the PySide6 IDE MVP."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
from app.services.supervisor_client import SupervisorClient


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class _InstallWorker(QThread):
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
        from supervisor.install_runner import run_install

        ide_config = self._settings_service.load().ide_config
        ida_mcp_config = self._settings_service.load().ida_mcp_config

        python_path = ide_config.python_path or ida_mcp_config.ida_python
        if not python_path:
            self.progress.emit("[ERROR] No Python executable configured")
            from supervisor.models import InstallationActionResult, InstallationCheck

            self.finished.emit(
                InstallationActionResult(
                    action="install",
                    ok=False,
                    summary="no Python executable configured",
                    check=InstallationCheck(
                        plugin_dir=ide_config.plugin_dir,
                        plugin_dir_exists=bool(
                            ide_config.plugin_dir
                            and Path(ide_config.plugin_dir).exists()
                        ),
                        config_path=None,
                        config_exists=False,
                        python_executable=None,
                        python_exists=False,
                        ida_mcp_py_exists=False,
                        ida_mcp_package_exists=False,
                        summary="no python",
                        warnings=["no Python executable"],
                    ),
                    warnings=["no Python executable"],
                )
            )
            return

        config_dict = ida_mcp_config.to_dict()
        result = run_install(
            python_executable=python_path,
            ida_path=ida_mcp_config.ida_path or ide_config.ida_path,
            plugin_dir=ide_config.plugin_dir,
            ida_mcp_config_dict=config_dict,
            on_progress=self.progress.emit,
        )
        self.finished.emit(result)


class SettingsPage(QWidget):
    language_changed = Signal(str)

    def __init__(
        self,
        settings_service: SettingsService | SupervisorClient | None = None,
    ) -> None:
        super().__init__()
        if isinstance(settings_service, SupervisorClient):
            self._settings_service = SettingsService(settings_service)
        else:
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

        self._python_path = QLineEdit()
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

        self._build_ui()
        self._apply_snapshot(initial_snapshot)

    def _t(self, key: str, **kwargs: object) -> str:
        return self._i18n.t(key, **kwargs)

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
        ):
            item = QListWidgetItem(name)
            font = item.font()
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

    def reload(self) -> None:
        self._apply_snapshot(self._settings_service.load())

    def _apply_snapshot(self, snapshot) -> None:
        previous_language = self._language
        self._language = normalize_language(snapshot.ide_config.language)
        self._i18n.set_language(self._language)
        self._refresh_language_combo()

        form_state = snapshot_to_form_state(snapshot)
        self._python_path.setText(form_state.python_path)
        self._plugin_dir.setText(form_state.plugin_dir)
        self._ide_request_timeout.setValue(form_state.ide_request_timeout)
        self._install_python_path.setText(effective_install_python_path(snapshot))
        self._install_plugin_dir.setText(form_state.plugin_dir)
        self._save_hint_label.setText(self._t("settings.save_hint"))
        self._install_notes.setPlaceholderText(self._t("settings.install.placeholder"))
        self._apply_installation_check(self._settings_service.check_installation())

        self._enable_http.setChecked(form_state.enable_http)
        self._enable_stdio.setChecked(form_state.enable_stdio)
        self._enable_unsafe.setChecked(form_state.enable_unsafe)
        self._wsl_path_bridge.setChecked(form_state.wsl_path_bridge)
        self._http_host.setText(form_state.http_host)
        self._http_port.setValue(form_state.http_port)
        self._http_path.setText(form_state.http_path)
        self._ida_default_port.setValue(form_state.ida_default_port)
        self._ida_host.setText(form_state.ida_host)
        self._ida_path.setText(form_state.ida_path)
        self._ida_python.setText(form_state.ida_python)
        self._open_in_ida_bundle_dir.setText(form_state.open_in_ida_bundle_dir)
        self._open_in_ida_autonomous.setChecked(form_state.open_in_ida_autonomous)
        self._auto_start.setChecked(form_state.auto_start)
        self._server_name.setText(form_state.server_name)
        self._ida_request_timeout.setValue(form_state.ida_request_timeout)
        self._debug.setChecked(form_state.debug)
        self._sync_wsl_bridge_fields()
        if self._language != previous_language:
            self.language_changed.emit(self._language)

    def save(self) -> None:
        self._save_settings(show_message=True)

    def _save_settings(self, *, show_message: bool) -> None:
        form_state = self._collect_form_state()
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
        installation = self._settings_service.check_installation()
        self._apply_installation_check(installation)
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

        self._install_worker = _InstallWorker(self._settings_service, parent=self)
        self._install_worker.progress.connect(self._on_install_progress)
        self._install_worker.finished.connect(self._on_install_finished)
        self._install_worker.start()

    def _on_install_progress(self, message: str) -> None:
        self._install_notes.append(message)

    def _on_install_finished(self, result: object) -> None:
        self._set_install_buttons_enabled(True)
        from supervisor.models import InstallationActionResult

        if not isinstance(result, InstallationActionResult):
            self._install_notes.append("[ERROR] Unexpected result type")
            return
        self._apply_installation_check(result.check)
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

    def _collect_form_state(self) -> SettingsFormState:
        return SettingsFormState(
            python_path=self._python_path.text(),
            plugin_dir=self._plugin_dir.text(),
            language=str(self._language_combo.currentData() or self._language),
            ide_request_timeout=self._ide_request_timeout.value(),
            enable_http=self._enable_http.isChecked(),
            enable_stdio=self._enable_stdio.isChecked(),
            enable_unsafe=self._enable_unsafe.isChecked(),
            wsl_path_bridge=self._wsl_path_bridge.isChecked(),
            http_host=self._http_host.text(),
            http_port=self._http_port.value(),
            http_path=self._http_path.text(),
            ida_default_port=self._ida_default_port.value(),
            ida_host=self._ida_host.text(),
            ida_path=self._ida_path.text(),
            ida_python=self._ida_python.text(),
            open_in_ida_bundle_dir=self._open_in_ida_bundle_dir.text(),
            open_in_ida_autonomous=self._open_in_ida_autonomous.isChecked(),
            auto_start=self._auto_start.isChecked(),
            server_name=self._server_name.text(),
            ida_request_timeout=self._ida_request_timeout.value(),
            debug=self._debug.isChecked(),
        )

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

    def _apply_installation_check(self, installation) -> None:
        self._requirements_path.setText(
            installation.requirements_path
            or self._t("settings.install.requirements.missing")
        )
        self._requirements_table.setHorizontalHeaderLabels(
            [
                self._t("settings.install.table.package"),
                self._t("settings.install.table.required"),
                self._t("settings.install.table.installed"),
            ]
        )
        rows = self._build_requirement_rows(installation)
        self._requirements_table.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            for column_index, value in enumerate(row_values):
                self._requirements_table.setItem(
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

    def _requirement_package_name(self, requirement: str) -> str:
        for index, char in enumerate(requirement):
            if not (char.isalnum() or char in "._-"):
                return requirement[:index]
        return requirement

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

        self._advanced_runtime_group = self._build_config_group(
            self._t("settings.group.runtime"),
            self._t("settings.group.runtime.desc"),
            [
                self._build_field_row(
                    self._t("settings.field.python_path"),
                    self._t("settings.field.python_path.desc"),
                    self._path_field(self._python_path, self._browse_file),
                ),
            ],
        )
        self._advanced_layout.addWidget(self._advanced_runtime_group)
