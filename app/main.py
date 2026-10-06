from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.ui.main_window import ShopManagerMainWindow


def main() -> int:
    app = QApplication([])
    app.setApplicationName("Shop Manager")

    window = ShopManagerMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
