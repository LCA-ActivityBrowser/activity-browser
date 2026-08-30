# -*- coding: utf-8 -*-
"""Settings → Plugins master/detail chapter."""
from loguru import logger
from qtpy import QtCore, QtWidgets

from activity_browser.app import settings
from activity_browser.app.pages.settings.base import BaseSettingsChapter
from activity_browser.plugins import loader as plugin_loader
from activity_browser.plugins.context import global_plugins_settings


_STATUS_LABELS = {
    "disabled": "Disabled",
    "enabled": "Enabled",
    "failed": "Failed",
    "incompatible": "Incompatible",
}


class PluginsSettingsChapter(BaseSettingsChapter):
    """Discover entry-point plugins; enable/disable globally (restart to apply)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._records = []
        self._enabled = set()

        self.plugin_list = QtWidgets.QListWidget()
        self.plugin_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.plugin_list.setMinimumWidth(180)

        self.detail = QtWidgets.QWidget()
        self.title_label = QtWidgets.QLabel()
        self.title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        self.meta_label = QtWidgets.QLabel()
        self.meta_label.setWordWrap(True)
        self.meta_label.setStyleSheet("color: #666;")
        self.summary_label = QtWidgets.QLabel()
        self.summary_label.setWordWrap(True)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        self.enable_check = QtWidgets.QCheckBox("Enable this plugin")
        self.restart_banner = QtWidgets.QLabel(
            "<b>Restart required</b> — save settings and restart Activity Browser "
            "for enable/disable changes to take effect."
        )
        self.restart_banner.setWordWrap(True)
        self.restart_banner.setStyleSheet(
            "background: #fef3c7; border: 1px solid #f6d98a; padding: 8px;"
        )
        self.empty_label = QtWidgets.QLabel(
            "No plugins discovered. Install a package that registers "
            "the activity_browser.plugins entry point."
        )
        self.empty_label.setWordWrap(True)

        self.build_layout()
        self.connect_signals()
        self.reset()

    def connect_signals(self):
        self.plugin_list.currentRowChanged.connect(self._on_selection)
        self.enable_check.toggled.connect(self._on_enable_toggled)

    def build_layout(self):
        detail_layout = QtWidgets.QVBoxLayout(self.detail)
        detail_layout.addWidget(self.title_label)
        detail_layout.addWidget(self.meta_label)
        detail_layout.addWidget(self.summary_label)
        detail_layout.addWidget(self.status_label)
        detail_layout.addWidget(self.enable_check)
        detail_layout.addStretch()

        split = QtWidgets.QSplitter()
        split.addWidget(self.plugin_list)
        split.addWidget(self.detail)
        split.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.restart_banner)
        layout.addWidget(self.empty_label)
        layout.addWidget(split, 1)
        self.setLayout(layout)
        self._split = split

    def _pending_restart(self) -> bool:
        """True when UI enablement differs from what this process applied at startup."""
        return set(self._enabled) != set(plugin_loader.applied_enabled_ids)

    def _update_restart_banners(self):
        self.restart_banner.setVisible(self._pending_restart())

    def _status_text(self, record) -> str:
        label = _STATUS_LABELS.get(record.status, record.status)
        if record.error:
            return f"{label}: {record.error}"
        return label

    def _refresh_list(self):
        self.plugin_list.clear()
        for record in self._records:
            item = QtWidgets.QListWidgetItem(
                f"{record.display_name}\n{_STATUS_LABELS.get(record.status, record.status)}"
            )
            item.setData(QtCore.Qt.UserRole, record.plugin_id)
            self.plugin_list.addItem(item)

        empty = not self._records
        self.empty_label.setVisible(empty)
        self._split.setVisible(not empty)
        self._update_restart_banners()
        if self._records:
            self.plugin_list.setCurrentRow(0)
        else:
            self._clear_detail()

    def _clear_detail(self):
        self.title_label.setText("")
        self.meta_label.setText("")
        self.summary_label.setText("")
        self.status_label.setText("")
        self.enable_check.blockSignals(True)
        self.enable_check.setChecked(False)
        self.enable_check.setEnabled(False)
        self.enable_check.blockSignals(False)

    def _on_selection(self, row: int):
        if row < 0 or row >= len(self._records):
            self._clear_detail()
            return
        record = self._records[row]
        self.title_label.setText(record.display_name)
        meta_bits = [f"Entry point: {record.plugin_id}"]
        if record.dist_name:
            ver = f" {record.dist_version}" if record.dist_version else ""
            meta_bits.append(f"Package: {record.dist_name}{ver}")
        self.meta_label.setText(" · ".join(meta_bits))
        self.summary_label.setText(record.summary or "")
        self.status_label.setText(f"Status: {self._status_text(record)}")

        incompatible = record.status == "incompatible"
        self.enable_check.blockSignals(True)
        self.enable_check.setEnabled(not incompatible)
        self.enable_check.setChecked(record.plugin_id in self._enabled)
        self.enable_check.blockSignals(False)
        self._update_restart_banners()

    def _on_enable_toggled(self, checked: bool):
        row = self.plugin_list.currentRow()
        if row < 0 or row >= len(self._records):
            return
        plugin_id = self._records[row].plugin_id
        if checked:
            self._enabled.add(plugin_id)
        else:
            self._enabled.discard(plugin_id)
        self._update_restart_banners()
        self.changed.emit()

    def get_current_state(self):
        return sorted(self._enabled)

    def reset(self):
        saved = set(global_plugins_settings(settings).get("enabled_plugins") or [])
        self._enabled = set(saved)
        # Prefer last load records; if empty, synthesize from discovery metadata only.
        self._records = list(plugin_loader.plugin_records)
        if not self._records:
            try:
                for ep in plugin_loader.discover_entry_points():
                    self._records.append(
                        plugin_loader.PluginRecord(
                            plugin_id=ep.name,
                            display_name=ep.name,
                            enabled=ep.name in self._enabled,
                            status="disabled",
                        )
                    )
            except Exception as exc:
                logger.warning("Could not discover plugins for Settings: {}", exc)
        self._refresh_list()
        self._initial_state = self.get_current_state()

    def has_changes(self):
        saved = sorted(global_plugins_settings(settings).get("enabled_plugins") or [])
        return sorted(self._enabled) != saved

    def set_settings(self):
        plugins = global_plugins_settings(settings)
        plugins["enabled_plugins"] = sorted(self._enabled)
        logger.info("Saved enabled plugins: {}", plugins["enabled_plugins"])
        self._update_restart_banners()
