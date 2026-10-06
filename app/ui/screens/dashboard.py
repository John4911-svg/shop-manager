from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderScreen(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet(
            "font-size: 22px; font-weight: 600; margin-bottom: 10px;"
        )

        placeholder = QLabel(f"{title} screen\nPlaceholder for future V1 functionality")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #5c5c5c; font-size: 15px;")

        layout.addWidget(heading)
        layout.addWidget(placeholder)

