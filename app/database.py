from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB_FILENAME = "shop.db"
CURRENT_SCHEMA_VERSION = 1

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT UNIQUE,
    category_id INTEGER,
    unit TEXT NOT NULL,
    cost_price INTEGER NOT NULL CHECK(cost_price >= 0),
    selling_price INTEGER NOT NULL CHECK(selling_price >= 0),
    stock_quantity REAL NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
    reorder_level REAL NOT NULL DEFAULT 0 CHECK(reorder_level >= 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_number TEXT NOT NULL UNIQUE,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal INTEGER NOT NULL CHECK(subtotal >= 0),
    total_amount INTEGER NOT NULL CHECK(total_amount >= 0),
    total_cost INTEGER NOT NULL CHECK(total_cost >= 0),
    gross_profit INTEGER NOT NULL,
    payment_method TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL CHECK(quantity > 0),
    unit_price INTEGER NOT NULL CHECK(unit_price >= 0),
    unit_cost INTEGER NOT NULL CHECK(unit_cost >= 0),
    subtotal INTEGER NOT NULL CHECK(subtotal >= 0),
    profit INTEGER NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    quantity REAL NOT NULL CHECK(quantity != 0),
    quantity_before REAL NOT NULL CHECK(quantity_before >= 0),
    quantity_after REAL NOT NULL CHECK(quantity_after >= 0),
    reference_id INTEGER,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK(amount > 0),
    expense_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product_id ON sale_items(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_created_at ON stock_movements(created_at);
CREATE INDEX IF NOT EXISTS idx_sales_timestamp ON sales(timestamp);
CREATE INDEX IF NOT EXISTS idx_expenses_expense_date ON expenses(expense_date);
"""

SCHEMA_VERSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_app_data_dir() -> Path:
    """Return a predictable app data directory for persisted local data."""
    if sys.platform.startswith("win"):
        base_dir = Path(__import__("os").environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        base_dir = Path(__import__("os").environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    app_dir = base_dir / "ShopManager"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir.resolve()


class DatabaseManager:
    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            self.db_path = get_app_data_dir() / DB_FILENAME
        else:
            self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize(self) -> sqlite3.Connection:
        connection = self.connect()
        try:
            self._ensure_schema(connection)
            return connection
        except Exception:
            connection.close()
            raise

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(SCHEMA_VERSION_TABLE_SQL)
        current_version = self._get_schema_version(connection)

        if current_version is None:
            connection.executescript(CREATE_TABLES_SQL)
            connection.executescript(CREATE_INDEXES_SQL)
            self._set_schema_version(connection, CURRENT_SCHEMA_VERSION)
            connection.commit()
            return

        if current_version < CURRENT_SCHEMA_VERSION:
            connection.executescript(CREATE_TABLES_SQL)
            connection.executescript(CREATE_INDEXES_SQL)
            self._set_schema_version(connection, CURRENT_SCHEMA_VERSION)
            connection.commit()
            return

        connection.executescript(CREATE_INDEXES_SQL)
        connection.commit()

    def _get_schema_version(self, connection: sqlite3.Connection) -> int | None:
        row = connection.execute(
            "SELECT version FROM schema_version WHERE id = 1"
        ).fetchone()
        return None if row is None else int(row["version"])

    def _set_schema_version(self, connection: sqlite3.Connection, version: int) -> None:
        connection.execute(
            """
            INSERT INTO schema_version (id, version, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                version = excluded.version,
                updated_at = CURRENT_TIMESTAMP
            """,
            (version,),
        )


def initialize_database(db_path: str | Path | None = None) -> DatabaseManager:
    manager = DatabaseManager(db_path)
    manager.initialize()
    return manager


def _assert_table_exists(connection: sqlite3.Connection, table_name: str) -> None:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    if row is None:
        raise AssertionError(f"Table '{table_name}' was not created.")


def verify_database() -> dict:
    """
    Run a set of integrity checks for the shop database schema.

    Uses a temporary in-memory test database so verification does not modify the real
    application database or leave test business data behind.
    """
    test_conn = sqlite3.connect(":memory:")
    test_conn.row_factory = sqlite3.Row
    test_conn.execute("PRAGMA foreign_keys = ON")

    try:
        test_conn.execute(SCHEMA_VERSION_TABLE_SQL)
        test_conn.executescript(CREATE_TABLES_SQL)
        test_conn.executescript(CREATE_INDEXES_SQL)
        test_conn.execute(
            "INSERT INTO schema_version (id, version, updated_at) VALUES (1, ?, CURRENT_TIMESTAMP)",
            (CURRENT_SCHEMA_VERSION,),
        )
        test_conn.commit()

        required_tables = [
            "users",
            "categories",
            "products",
            "sales",
            "sale_items",
            "stock_movements",
            "expenses",
        ]
        for table in required_tables:
            _assert_table_exists(test_conn, table)

        fk_enabled = test_conn.execute("PRAGMA foreign_keys").fetchone()[0]
        if fk_enabled != 1:
            raise AssertionError("SQLite foreign key enforcement is not enabled.")

        tables = [
            row["name"]
            for row in test_conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]

        test_conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("verification_user", "hash1"),
        )
        test_conn.commit()
        try:
            test_conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("verification_user", "hash2"),
            )
            test_conn.commit()
            raise AssertionError("Duplicate username was accepted when it should have failed.")
        except sqlite3.IntegrityError:
            test_conn.rollback()

        try:
            test_conn.execute(
                "INSERT INTO products (name, unit, cost_price, selling_price, stock_quantity, reorder_level) VALUES (?, ?, ?, ?, ?, ?)",
                ("BadCostProduct", "piece", -10, 100, 5, 1),
            )
            test_conn.commit()
            raise AssertionError("Negative product cost_price was accepted when it should have failed.")
        except sqlite3.IntegrityError:
            test_conn.rollback()

        try:
            test_conn.execute(
                "INSERT INTO products (name, unit, cost_price, selling_price, stock_quantity, reorder_level) VALUES (?, ?, ?, ?, ?, ?)",
                ("BadSellingProduct", "piece", 50, -10, 5, 1),
            )
            test_conn.commit()
            raise AssertionError("Negative product selling_price was accepted when it should have failed.")
        except sqlite3.IntegrityError:
            test_conn.rollback()

        try:
            test_conn.execute(
                "INSERT INTO products (name, unit, cost_price, selling_price, stock_quantity, reorder_level) VALUES (?, ?, ?, ?, ?, ?)",
                ("BadStockProduct", "kg", 50, 70, -2, 1),
            )
            test_conn.commit()
            raise AssertionError("Negative product stock_quantity was accepted when it should have failed.")
        except sqlite3.IntegrityError:
            test_conn.rollback()

        test_conn.execute(
            "INSERT INTO sales (sale_number, subtotal, total_amount, total_cost, gross_profit, payment_method) VALUES (?, ?, ?, ?, ?, ?)",
            ("SALE-VERIFICATION-001", 100, 100, 50, 50, "Cash"),
        )
        test_conn.commit()
        sale_row = test_conn.execute(
            "SELECT id FROM sales WHERE sale_number = ?", ("SALE-VERIFICATION-001",)
        ).fetchone()
        sale_id = sale_row["id"]

        test_conn.execute(
            "INSERT INTO products (name, unit, cost_price, selling_price, stock_quantity, reorder_level) VALUES (?, ?, ?, ?, ?, ?)",
            ("VerificationProduct", "piece", 50, 100, 10, 2),
        )
        test_conn.commit()
        product_row = test_conn.execute(
            "SELECT id FROM products WHERE name = ?", ("VerificationProduct",)
        ).fetchone()
        product_id = product_row["id"]

        try:
            test_conn.execute(
                "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, unit_cost, subtotal, profit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sale_id, product_id, 0, 10, 5, 0, 5),
            )
            test_conn.commit()
            raise AssertionError("Zero quantity sale item was accepted when it should have failed.")
        except sqlite3.IntegrityError:
            test_conn.rollback()

        try:
            test_conn.execute(
                "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, unit_cost, subtotal, profit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sale_id, product_id, -5, 10, 5, -50, 5),
            )
            test_conn.commit()
            raise AssertionError("Negative sale quantity was accepted when it should have failed.")
        except sqlite3.IntegrityError:
            test_conn.rollback()

        try:
            test_conn.execute(
                "INSERT INTO expenses (category, description, amount, expense_date) VALUES (?, ?, ?, ?)",
                ("Utilities", "Power bill", -50, "2026-10-05"),
            )
            test_conn.commit()
            raise AssertionError("Negative expense amount was accepted when it should have failed.")
        except sqlite3.IntegrityError:
            test_conn.rollback()

        try:
            test_conn.execute(
                "INSERT INTO products (name, unit, category_id, cost_price, selling_price, stock_quantity, reorder_level) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("BadCategoryProduct", "piece", 9999, 50, 75, 10, 2),
            )
            test_conn.commit()
            raise AssertionError("Invalid product category_id foreign key was accepted when it should have failed.")
        except sqlite3.IntegrityError:
            test_conn.rollback()

        test_conn.execute("INSERT INTO categories (name) VALUES (?)", ("Groceries",))
        test_conn.commit()
        category_row = test_conn.execute("SELECT id FROM categories WHERE name = ?", ("Groceries",)).fetchone()
        category_id = category_row["id"]

        test_conn.execute(
            "INSERT INTO products (name, sku, category_id, unit, cost_price, selling_price, stock_quantity, reorder_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("Rice", "RICE-001", category_id, "kg", 80, 120, 25, 5),
        )
        test_conn.commit()
        rice_row = test_conn.execute("SELECT id FROM products WHERE sku = ?", ("RICE-001",)).fetchone()
        rice_product_id = rice_row["id"]

        test_conn.execute(
            "INSERT INTO stock_movements (product_id, movement_type, quantity, quantity_before, quantity_after, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (rice_product_id, "OPENING", 25, 0, 25, "Initial stock"),
        )
        test_conn.commit()

        test_conn.execute(
            "INSERT INTO sales (sale_number, subtotal, total_amount, total_cost, gross_profit, payment_method) VALUES (?, ?, ?, ?, ?, ?)",
            ("SALE-VERIFICATION-002", 120, 120, 80, 40, "Cash"),
        )
        test_conn.commit()
        sale2_row = test_conn.execute(
            "SELECT id FROM sales WHERE sale_number = ?", ("SALE-VERIFICATION-002",)
        ).fetchone()
        sale2_id = sale2_row["id"]

        test_conn.execute(
            "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, unit_cost, subtotal, profit) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sale2_id, rice_product_id, 1, 120, 80, 120, 40),
        )
        test_conn.commit()

        return {
            "status": "PASSED",
            "tables": tables,
            "foreign_keys_enabled": bool(fk_enabled),
            "schema_version": CURRENT_SCHEMA_VERSION,
            "checks_performed": [
                "All 7 tables created",
                "Foreign key enforcement enabled",
                "Duplicate username constraint",
                "Negative cost_price constraint",
                "Negative selling_price constraint",
                "Negative stock_quantity constraint",
                "Zero quantity sale_item constraint",
                "Negative quantity sale_item constraint",
                "Negative expense amount constraint",
                "Invalid category_id foreign key constraint",
                "Valid category->product->stock_movement relationship",
                "Valid sale->sale_item->product relationship",
            ],
        }
    finally:
        test_conn.close()


if __name__ == "__main__":
    result = verify_database()
    print("Temporary verification database passed.")
    print(result)
