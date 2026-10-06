# Shop Manager - Operation-to-Layer Mapping

## Overview

This document maps each V1 operation to the correct architectural component:

- UI Layer
- Service Layer
- Repository / Data Access Layer
- Database Tables
- Transaction Boundary

The goal is to remove ambiguity before implementation begins.

---

## 1. Architecture Rules for All Operations

### 1.1 Layer ownership

- The UI collects input and displays results.
- The Service decides the business workflow and owns transaction orchestration.
- The Repository performs SQL work inside the service-controlled transaction.
- The Database stores the actual data and enforces constraints.

### 1.2 Transaction rule

Operations that modify multiple tables or business records must be handled in a service-owned transaction.

This includes:

- sale completion
- stock adjustments that affect inventory history
- opening stock creation
- restock operations that create stock movements
- any operation that must be all-or-nothing

---

## 2. Core Service and Repository Structure

### Services

- AuthService
- ProductService
- CategoryService
- InventoryService
- SalesService
- ExpenseService
- ReportService
- BackupService

### Repositories

- UserRepository
- ProductRepository
- CategoryRepository
- SaleRepository
- StockMovementRepository
- ExpenseRepository

### Database tables involved

- users
- categories
- products
- sales
- sale_items
- stock_movements
- expenses

---

## 3. Authentication Operations

### 3.1 Login user

| Field | Value |
| --- | --- |
| Operation | Login user |
| UI Layer | Show login form, capture username/password, call service |
| Service | AuthService.login(username, password) |
| Repository | UserRepository.get_by_username() |
| Tables | users |
| Transaction | No |
| Notes | Password must be verified against stored hash. No plaintext password stored in DB. |

### 3.2 Logout user

| Field | Value |
| --- | --- |
| Operation | Logout user |
| UI Layer | Trigger logout action |
| Service | AuthService.logout() |
| Repository | None required |
| Tables | None |
| Transaction | No |
| Notes | UI/session state handled locally; no database write required. |

### 3.3 Validate authenticated session

| Field | Value |
| --- | --- |
| Operation | Validate authenticated session |
| UI Layer | Check current auth state before screen access |
| Service | AuthService.validate_session() |
| Repository | UserRepository.get_by_id() |
| Tables | users |
| Transaction | No |
| Notes | Ensures logged-in user is active and valid. |

---

## 4. Product Operations

### 4.1 Create product

| Field | Value |
| --- | --- |
| Operation | Create product |
| UI Layer | Product form -> validate input -> call ProductService.create_product() |
| Service | ProductService.create_product(product_data) |
| Repository | ProductRepository.insert(product) |
| Tables | products |
| Transaction | No (unless accompanied by opening stock movement) |
| Notes | Non-empty name, unit, valid prices, non-negative stock. Optional opening stock may generate an OPENING stock movement in a separate business flow. |

### 4.2 Get product by id

| Field | Value |
| --- | --- |
| Operation | Read single product |
| UI Layer | Show product detail or edit form |
| Service | ProductService.get_product(product_id) |
| Repository | ProductRepository.get_by_id(product_id) |
| Tables | products |
| Transaction | No |
| Notes | Fetches current product values. |

### 4.3 List products

| Field | Value |
| --- | --- |
| Operation | List products |
| UI Layer | Product list view |
| Service | ProductService.list_products() |
| Repository | ProductRepository.list_all() |
| Tables | products |
| Transaction | No |
| Notes | Can optionally filter by category or active status. |

### 4.4 Update product

| Field | Value |
| --- | --- |
| Operation | Update product |
| UI Layer | Product form -> call ProductService.update_product() |
| Service | ProductService.update_product(product_id, changes) |
| Repository | ProductRepository.update(product_id, changes) |
| Tables | products |
| Transaction | No |
| Notes | Price updates are allowed; historical sale records remain unchanged because sale_items stores price snapshots. |

### 4.5 Deactivate product

| Field | Value |
| --- | --- |
| Operation | Deactivate product |
| UI Layer | Toggle active status |
| Service | ProductService.deactivate_product(product_id) |
| Repository | ProductRepository.update_status(product_id, False) |
| Tables | products |
| Transaction | No |
| Notes | Historical sales remain untouched. Deactivated products cannot be sold in new sales. |

### 4.6 Reorder level update

| Field | Value |
| --- | --- |
| Operation | Set or update reorder level |
| UI Layer | Product settings or inventory form |
| Service | ProductService.set_reorder_level(product_id, level) |
| Repository | ProductRepository.update_reorder_level(product_id, level) |
| Tables | products |
| Transaction | No |
| Notes | Used in low-stock and alert logic. |

---

## 5. Category Operations

### 5.1 Create category

| Field | Value |
| --- | --- |
| Operation | Create category |
| UI Layer | Category form -> call CategoryService.create_category() |
| Service | CategoryService.create_category(category_data) |
| Repository | CategoryRepository.insert(category) |
| Tables | categories |
| Transaction | No |
| Notes | Name must be non-empty and unique. |

### 5.2 List categories

| Field | Value |
| --- | --- |
| Operation | List categories |
| UI Layer | Category selection/list screen |
| Service | CategoryService.list_categories() |
| Repository | CategoryRepository.list_all() |
| Tables | categories |
| Transaction | No |
| Notes | Supports product filtering and reporting labels. |

### 5.3 Update category

| Field | Value |
| --- | --- |
| Operation | Update category |
| UI Layer | Edit category form |
| Service | CategoryService.update_category(category_id, changes) |
| Repository | CategoryRepository.update(category_id, changes) |
| Tables | categories |
| Transaction | No |
| Notes | Only name changes are typically allowed. |

---

## 6. Inventory Operations

### 6.1 Record opening stock

| Field | Value |
| --- | --- |
| Operation | Record opening stock |
| UI Layer | Product initial stock form |
| Service | InventoryService.record_opening_stock(product_id, quantity) |
| Repository | ProductRepository.update_stock(product_id, new_quantity), StockMovementRepository.insert(...) |
| Tables | products, stock_movements |
| Transaction | Yes |
| Notes | Must create an OPENING row and update stock quantity atomically. |

### 6.2 Record restock

| Field | Value |
| --- | --- |
| Operation | Restock product |
| UI Layer | Restock form |
| Service | InventoryService.restock(product_id, quantity, reason) |
| Repository | ProductRepository.update_stock(product_id, new_quantity), StockMovementRepository.insert(...) |
| Tables | products, stock_movements |
| Transaction | Yes |
| Notes | Must validate quantity > 0 and create one RESTOCK movement. |

### 6.3 Record adjustment

| Field | Value |
| --- | --- |
| Operation | Adjustment stock change |
| UI Layer | Adjustment form |
| Service | InventoryService.adjust_stock(product_id, delta_quantity, reason) |
| Repository | ProductRepository.update_stock(product_id, new_quantity), StockMovementRepository.insert(...) |
| Tables | products, stock_movements |
| Transaction | Yes |
| Notes | Must validate non-zero quantity and ensure stock remains non-negative. |

### 6.4 Get stock status

| Field | Value |
| --- | --- |
| Operation | Determine stock status |
| UI Layer | Dashboard card or product grid |
| Service | InventoryService.get_stock_status(product) |
| Repository | ProductRepository.get_by_id(product_id) |
| Tables | products |
| Transaction | No |
| Notes | Status rules: OUT OF STOCK, LOW STOCK, NORMAL. |

### 6.5 Get stock movement history

| Field | Value |
| --- | --- |
| Operation | View stock movement history |
| UI Layer | Inventory movement log |
| Service | InventoryService.get_stock_movements(product_id) |
| Repository | StockMovementRepository.list_by_product(product_id) |
| Tables | stock_movements |
| Transaction | No |
| Notes | Used for auditing and reporting. |

---

## 7. Sales Operations

### 7.1 Add item to cart

| Field | Value |
| --- | --- |
| Operation | Add product to cart |
| UI Layer | Shopping cart UI |
| Service | SalesService.add_item_to_cart(product_id, quantity) |
| Repository | ProductRepository.get_by_id(product_id) |
| Tables | products |
| Transaction | No |
| Notes | UI or service holds cart state temporarily. No database write yet. |

### 7.2 Remove item from cart

| Field | Value |
| --- | --- |
| Operation | Remove product from cart |
| UI Layer | Cart actions |
| Service | SalesService.remove_item_from_cart(product_id) |
| Repository | None required |
| Tables | None |
| Transaction | No |
| Notes | Local cart state only. |

### 7.3 Validate sale

| Field | Value |
| --- | --- |
| Operation | Validate cart before committing |
| UI Layer | UI triggers finalization |
| Service | SalesService.validate_sale(cart, payment_method) |
| Repository | ProductRepository.get_products_for_sale(cart_items), maybe ProductRepository.get_by_id() |
| Tables | products |
| Transaction | No |
| Notes | Confirms cart not empty, items exist, active, valid quantity, stock available, payment method valid, price data available. |

### 7.4 Complete sale

| Field | Value |
| --- | --- |
| Operation | Finalize and save sale |
| UI Layer | Finalize sale button |
| Service | SalesService.complete_sale(cart, payment_method) |
| Repository | SaleRepository.insert_sale(...), SaleRepository.insert_sale_items(...), ProductRepository.update_stock(...), StockMovementRepository.insert(...) |
| Tables | sales, sale_items, products, stock_movements |
| Transaction | Yes — this is the critical all-or-nothing sale transaction |
| Notes | This is the most important service-owned transaction in V1. |

### 7.5 Get sale by id

| Field | Value |
| --- | --- |
| Operation | View sale details |
| UI Layer | Sale receipt/detail view |
| Service | SalesService.get_sale(sale_id) |
| Repository | SaleRepository.get_by_id(sale_id), SaleRepository.get_items_by_sale_id(sale_id) |
| Tables | sales, sale_items |
| Transaction | No |
| Notes | Used for historical review and receipts. |

### 7.6 List sales

| Field | Value |
| --- | --- |
| Operation | List recent sales |
| UI Layer | Sales history screen |
| Service | SalesService.list_sales() |
| Repository | SaleRepository.list_recent() |
| Tables | sales |
| Transaction | No |
| Notes | Used for daily reporting and sales history. |

---

## 8. Expense Operations

### 8.1 Record expense

| Field | Value |
| --- | --- |
| Operation | Create expense |
| UI Layer | Expense form |
| Service | ExpenseService.create_expense(expense_data) |
| Repository | ExpenseRepository.insert(expense) |
| Tables | expenses |
| Transaction | No |
| Notes | Expense amount must be > 0 and category/description/date must be valid. |

### 8.2 List expenses

| Field | Value |
| --- | --- |
| Operation | List expenses |
| UI Layer | Expense report or ledger |
| Service | ExpenseService.list_expenses() |
| Repository | ExpenseRepository.list_all() |
| Tables | expenses |
| Transaction | No |
| Notes | Used for net profit calculation and reporting. |

### 8.3 Delete expense

| Field | Value |
| --- | --- |
| Operation | Delete expense |
| UI Layer | Delete expense action |
| Service | ExpenseService.delete_expense(expense_id) |
| Repository | ExpenseRepository.delete_by_id(expense_id) |
| Tables | expenses |
| Transaction | No |
| Notes | If deletion is allowed in V1, it should be controlled as a business action. If not allowed, update documentation accordingly. |

---

## 9. Reporting Operations

### 9.1 Daily sales summary

| Field | Value |
| --- | --- |
| Operation | Aggregate sales for a given day |
| UI Layer | Dashboard card or report screen |
| Service | ReportService.get_daily_sales_summary(date) |
| Repository | SaleRepository.get_daily_sales(date) |
| Tables | sales |
| Transaction | No |
| Notes | Uses saved sales records; no temporary UI calculations. |

### 9.2 Daily profit report

| Field | Value |
| --- | --- |
| Operation | Aggregate daily profit |
| UI Layer | Report view |
| Service | ReportService.get_daily_profit_report(date) |
| Repository | SaleRepository.get_daily_sales(date), ExpenseRepository.get_daily_expenses(date) |
| Tables | sales, sale_items, expenses |
| Transaction | No |
| Notes | Revenue, COGS, and gross profit are derived from sale records. |

### 9.3 Product profitability report

| Field | Value |
| --- | --- |
| Operation | Show profitability by product |
| UI Layer | Profitability report |
| Service | ReportService.get_product_profitability() |
| Repository | SaleRepository.get_profitability_by_product(), ProductRepository.list_all() |
| Tables | sales, sale_items, products |
| Transaction | No |
| Notes | Uses historical sale item values to preserve accuracy. |

### 9.4 Stock report

| Field | Value |
| --- | --- |
| Operation | Display stock inventory summary |
| UI Layer | Stock report view |
| Service | ReportService.get_stock_report() |
| Repository | ProductRepository.list_all(), StockMovementRepository.list_recent() |
| Tables | products, stock_movements |
| Transaction | No |
| Notes | Includes current stock and movement history. |

### 9.5 Low-stock and out-of-stock alerts

| Field | Value |
| --- | --- |
| Operation | Identify low stock / out of stock products |
| UI Layer | Alerts panel or dashboard |
| Service | ReportService.get_stock_alerts() |
| Repository | ProductRepository.list_all() |
| Tables | products |
| Transaction | No |
| Notes | Derived from `stock_quantity` and `reorder_level`. |

### 9.6 Dashboard KPI summary

| Field | Value |
| --- | --- |
| Operation | Display business dashboard KPIs |
| UI Layer | Dashboard screen |
| Service | ReportService.get_dashboard_summary() |
| Repository | SaleRepository.get_kpis(), ExpenseRepository.get_expense_total(), ProductRepository.get_stock_overview() |
| Tables | sales, sale_items, expenses, products |
| Transaction | No |
| Notes | Dashboard uses saved operational data, not transient memory. |

---

## 10. Backup and Restore Operations

### 10.1 Backup database

| Field | Value |
| --- | --- |
| Operation | Create database backup |
| UI Layer | Backup action |
| Service | BackupService.backup_database() |
| Repository | Database backup interface / file system interaction |
| Tables | All tables |
| Transaction | No (or internal file copy behavior) |
| Notes | Ensures database is backed up safely; no business logic should be lost. |

### 10.2 Restore database

| Field | Value |
| --- | --- |
| Operation | Restore database from backup |
| UI Layer | Restore action |
| Service | BackupService.restore_database(backup_file) |
| Repository | Database restore interface / file system I/O |
| Tables | All tables |
| Transaction | Potentially transactional or controlled restore process |
| Notes | Must be handled carefully and only by explicit user action. |

---

## 11. Operation Summary Matrix

| Operation | UI | Service | Repository | Tables | Transaction |
| --- | --- | --- | --- | --- | --- |
| Login | yes | AuthService | UserRepository | users | no |
| Create product | yes | ProductService | ProductRepository | products | no |
| Update product | yes | ProductService | ProductRepository | products | no |
| Deactivate product | yes | ProductService | ProductRepository | products | no |
| Create category | yes | CategoryService | CategoryRepository | categories | no |
| Record opening stock | yes | InventoryService | ProductRepository + StockMovementRepository | products, stock_movements | yes |
| Restock product | yes | InventoryService | ProductRepository + StockMovementRepository | products, stock_movements | yes |
| Adjustment stock | yes | InventoryService | ProductRepository + StockMovementRepository | products, stock_movements | yes |
| Add to cart | yes | SalesService | ProductRepository | products | no |
| Validate sale | yes | SalesService | ProductRepository | products | no |
| Complete sale | yes | SalesService | SaleRepository + ProductRepository + StockMovementRepository | sales, sale_items, products, stock_movements | yes |
| Record expense | yes | ExpenseService | ExpenseRepository | expenses | no |
| Daily sales report | yes | ReportService | SaleRepository | sales | no |
| Daily profit report | yes | ReportService | SaleRepository + ExpenseRepository | sales, sale_items, expenses | no |
| Product profitability report | yes | ReportService | SaleRepository + ProductRepository | sales, sale_items, products | no |
| Stock report | yes | ReportService | ProductRepository + StockMovementRepository | products, stock_movements | no |
| Backup database | yes | BackupService | backup interface | all tables | no |

---

## 12. Final Architecture Rule

The service layer owns the business flow and transaction boundary.

The repository layer owns the SQL and database operations.

The UI layer owns user interaction only.

This separation ensures:

- consistent business logic
- safer database writes
- correct sale atomicity
- clean implementation boundaries
- predictable V1 code structure

---

## 13. Implementation Guidance

Implementation should follow this order:

1. Define models
2. Define repositories
3. Define services
4. Wire UI to services
5. Add reporting logic from database records
6. Test validation and transaction behavior
7. Validate stock movement and sale atomicity

This mapping is intended to reduce uncertainty and ensure the architecture is implemented exactly as designed.
