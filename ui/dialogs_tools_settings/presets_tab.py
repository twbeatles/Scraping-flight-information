"""Settings dialog destination-preset tab (SRP: preset tab only)."""

from typing import Any

from PyQt6.QtWidgets import QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

import config


def build_presets_tab(dialog: Any) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("사용자 정의 프리셋 목록:"))
    dialog.list_presets = QListWidget()
    refresh_presets(dialog)
    layout.addWidget(dialog.list_presets)

    btn_del = QPushButton("선택 삭제")
    btn_del.clicked.connect(dialog._delete_preset)
    layout.addWidget(btn_del)

    return widget


def refresh_presets(dialog: Any) -> None:
    dialog.list_presets.clear()
    presets = dialog.prefs.get_all_presets()
    for code, name in presets.items():
        if code not in config.AIRPORTS:  # Only show custom ones
            dialog.list_presets.addItem(f"{code} - {name}")


def delete_selected_preset(dialog: Any) -> None:
    item = dialog.list_presets.currentItem()
    if item:
        code = item.text().split(' - ')[0]
        dialog.prefs.remove_preset(code)
        refresh_presets(dialog)
