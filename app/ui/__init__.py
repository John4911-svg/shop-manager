from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

from app.ui.screens.dashboard import DashboardScreen
from app.ui.screens.expenses import ExpensesScreen
from app.ui.screens.inventory import InventoryScreen
from app.ui.screens.products import ProductsScreen
from app.ui.screens.reports import ReportsScreen
from app.ui.screens.sales import SalesScreen
from app.ui.screens.sell import SellScreen
from app.ui.screens.settings import SettingsScreen


NAV_ITEMS = [
    "Dashboard",
    "Sell",
    "Products",
    "Inventory",
    "Sales",
    "Expenses",
    "Reports",
    "Settings",
    "Logout",
]


class ShopManagerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Shop Manager")
        self.resize(1280, 760)

        icon_path = Path(__file__).resolve().parents[1] / "resources" / "icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.navigation = QListWidget()
        self.navigation.setFixedWidth(220)
        self.navigation.setUniformItemSizes(True)
        self.navigation.setAlternatingRowColors(True)

        for label in NAV_ITEMS:
            self.navigation.addItem(label)

        self.navigation.currentRowChanged.connect(self._switch_screen)

        self.stacked_pages = QStackedWidget()
        self.pages = {
            "Dashboard": DashboardScreen(),
            "Sell": SellScreen(),
            "Products": ProductsScreen(),
            "Inventory": InventoryScreen(),
            "Sales": SalesScreen(),
            "Expenses": ExpensesScreen(),
            "Reports": ReportsScreen(),
            "Settings": SettingsScreen(),
            "Logout": DashboardScreen("Logout"),
        }

        for page in self.pages.values():
            self.stacked_pages.addWidget(page)

        layout.addWidget(self.navigation)
        layout.addWidget(self.stacked_pages)

        self.navigation.setCurrentRow(0)

    def _switch_screen(self, index: int) -> None:
        if 0 <= index < self.stacked_pages.count():
            self.stacked_pages.setCurrentIndex(index)


__all__ = ["ShopManagerMainWindow"]
