from __future__ import annotations

from app.database import verify_database


if __name__ == "__main__":
    result = verify_database()
    print("shop.db initialized successfully.")
    print(result)
