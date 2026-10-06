# Shop Manager - Architecture

## Overview

Shop Manager V1 is a single-user, offline-first desktop application built with PySide6 and backed by SQLite. It is designed to manage products, inventory, sales, expenses, and business reporting without requiring network access or a remote service.

The system is intentionally simple, reliable, and auditable. Every important business action must be stored in the database and must be consistent with the frozen V1 business rules.

---

## 1. Architectural Principles

### 1.1 Offline-first desktop architecture

- The application runs locally on the machine and stores all business data in SQLite.
- There is no dependency on a remote database or online payment system.
- Data persists after application shutdown and restart.
- The application is a local desktop experience, not a web application.

### 1.2 Single responsibility by layer

The system is separated into clear layers:

- UI layer: user interaction and display
- Business logic layer: validation, calculations, rules, workflows
- Service layer: orchestration of business actions and transaction ownership
- Repository/data-access layer: database read/write operations
- Database layer: tables, constraints, indexes, transactions

### 1.3 Data integrity first

The architecture must guarantee:

- No invalid data enters the database
- Sales are atomic
- Inventory never becomes negative
- Every stock change creates a stock movement record
- History is preserved for past sales
- Failed transactions rollback completely

### 1.4 Database as source of truth

The SQLite database is the system of record. Business reports must read from saved database records rather than temporary UI state.

---

## 2. Application Layers

## 2.1 UI Layer

Responsible for:

- Displaying products, stock, sales, and expenses
- Capturing user input
- Displaying validation error messages
- Showing dashboard/report data
- Handling user login and application navigation

The UI layer does not own business rules. It may call the service layer, but it must not directly mutate the database for critical business operations.

### Example responsibilities

- Login screen
- Product form
- Sale cart screen
- Dashboard screen
- Reports screen
- Expense entry screen

### Important rule

The UI must not perform critical logic like:

- calculating sale totals without business validation
- adjusting stock directly
- assuming a sale succeeded without transaction confirmation
- bypassing database constraints

---

## 2.2 Business Logic Layer

Responsible for:

- validating products, sales, stock changes, and expenses
- enforcing business rules
- calculating totals, gross profit, net profit, and profit margin
- determining stock status (normal, low stock, out of stock)
- protecting historical prices and data consistency

This layer sits between the UI and service layer.

### Business logic responsibilities

- Validate a sale before the transaction starts
- Confirm product exists and is active
- Confirm quantity is valid and available in stock
- Verify payment method is valid
- Compute sale item totals and sale totals
- Decide stock updates for each product
- Generate dashboard/report aggregates from database records

---

## 2.3 Service Layer

The service layer is responsible for transaction orchestration and business workflow control.

This is the layer that decides:

- when a transaction starts
- which repository operations belong inside the transaction
- whether the transaction commits or rolls back
- which errors are returned to the UI

This is especially important for the complete-sale workflow.

### Example service responsibilities

- `AuthService`: login and authentication workflow
- `ProductService`: product validation and inventory management workflows
- `CategoryService`: category management workflows
- `InventoryService`: stock updates, adjustments, and stock status logic
- `SalesService`: complete sale workflow including validation and transaction coordination
- `ExpenseService`: expense validation and recording
- `ReportService`: dashboard and financial reporting queries
- `BackupService`: backup and restore operations

### Service ownership of sales transaction

The `SalesService` owns the full sale transaction. It is the orchestration point for the entire operation.

Flow:

User finalizes cart
        ↓
SalesService
        ↓
Validate sale
        ↓
BEGIN TRANSACTION
        ↓
Repositories perform database operations
        ↓
COMMIT
        ↓
Return successful result to UI

On failure:

SalesService
        ↓
ROLLBACK
        ↓
Return controlled error to UI

This makes the architecture explicit and keeps transaction control out of the repository layer.

---

## 2.4 Repository / Data-Access Layer

Responsible for:

- database connection management
- SQL execution
- CRUD operations for tables
- transaction-aware data operations when called by a service
- querying business data for reports and dashboards

The repository layer performs the actual database operations using the connection/transaction supplied by the service.

### Relationship between Service and Repository

The intended structure is:

SalesService
    ↓
BEGIN TRANSACTION
    ↓
SaleRepository
ProductRepository
StockMovementRepository
    ↓
COMMIT / ROLLBACK

### Repository responsibilities

- `UserRepository`: user lookup and persistence
- `ProductRepository`: product lookup, update, stock adjustment
- `CategoryRepository`: category CRUD
- `SaleRepository`: sale header creation and sale retrieval
- `StockMovementRepository`: stock movement creation
- `ExpenseRepository`: expense CRUD

Repositories do not decide business transaction boundaries. They execute database work within the transaction the service controls.

---

## 2.5 Model Layer

The model layer represents the application's core business data.

V1 models correspond primarily to:

- `User`
- `Category`
- `Product`
- `Sale`
- `SaleItem`
- `StockMovement`
- `Expense`

### Model responsibilities

- Hold structured business data
- Validate basic object-level rules
- Expose fields in a straightforward Python data structure
- Represent information that is persisted in SQLite

### Important rules

- Models hold data and simple validation logic only.
- Models do not contain UI behavior.
- Models do not orchestrate database transactions.
- Models do not bypass the service layer to mutate the database.
- Keep this layer simple. Do not introduce an ORM merely because a model layer exists.

---

## 2.6 Database Layer

Responsible for:

- the SQLite schema
- foreign key enforcement
- indexes
- constraints
- transactions
- storage of business data and audit history

This is the technical foundation of the system.

The database is not just storage; it is the source of truth and must enforce integrity rules whenever possible.

---

## 3. Core Components

## 3.1 Authentication and User Management

- `users` table stores login credentials and active status
- Passwords are hashed before persistence
- Only authenticated users can access business functionality
- V1 supports a single primary operator; multi-user roles are out of scope

## 3.2 Product Management

- `products` table stores product details, current price, stock quantity, reorder level, and active status
- Product validation includes name, unit, cost_price, selling_price, stock_quantity, reorder_level
- Deactivation does not delete historical data
- Historical sales remain available even after product deactivation

## 3.3 Category Management

- `categories` table groups products logically
- Category data supports product organization and reporting

## 3.4 Inventory and Stock Movement Management

- `stock_movements` table tracks all stock changes
- Every valid stock update produces exactly one stock movement record
- Movement types include: OPENING, RESTOCK, SALE, ADJUSTMENT
- Stock movements are used for auditing and reports

## 3.5 Sales Management

- `sales` table stores sale header data
- `sale_items` table stores each product in a sale
- A sale is completed only if all validations pass and the transaction commits successfully
- Historical price capture is critical: each sale item stores unit_price and unit_cost

## 3.6 Expense Management

- `expenses` table stores business costs outside of sales
- Expenses are separate from sales and are later used in net profit calculations

## 3.7 Reporting and Dashboard

V1 dashboard and reports include:

- Daily sales summary
- Daily profit summary
- Product profitability summaries
- Stock report
- Low-stock alert report
- Out-of-stock report

Reports are created from real database records and should not rely on transient UI data.

---

## 4. Database Access Model

The database layer should provide a clean, narrow interface to the rest of the application, for example:

- `connect()`
- `initialize_database()`
- `get_product_by_id()`
- `create_product()`
- `update_product_stock()`
- `create_sale()`
- `create_sale_items()`
- `create_stock_movement()`
- `record_expense()`
- `get_daily_sales()`
- `get_profit_report()`
- `get_stock_report()`

The business service layer should call repositories, instead of directly writing ad hoc SQL across the whole app.

This keeps the repository layer stable and reduces duplication.

### Intended structure

Services
 ├── AuthService
 ├── ProductService
 ├── CategoryService
 ├── InventoryService
 ├── SalesService
 ├── ExpenseService
 ├── ReportService
 └── BackupService

Repositories
 ├── UserRepository
 ├── ProductRepository
 ├── CategoryRepository
 ├── SaleRepository
 ├── StockMovementRepository
 └── ExpenseRepository

---

## 5. Sale Workflow

## 5.1 End-to-End Flow

User finalizes cart
        ↓
SalesService
        ↓
Validate sale
        ↓
BEGIN TRANSACTION
        ↓
Repositories perform database operations
        ↓
COMMIT TRANSACTION
        ↓
Sale successfully completed

## 5.2 Validation Workflow

Before the transaction begins, the application must verify:

- Product exists
- Product is active
- Requested quantity > 0
- Requested quantity <= available stock
- Product has current selling price and cost price
- Payment method is valid
- Business calculations can be performed correctly
- Cart is not empty

Only after all checks pass should the database transaction open.

## 5.3 Stock Update Workflow

For every sold product:

```text
stock_before = current stock
quantity_sold = sale quantity
stock_after = stock_before - quantity_sold
```

Then create a `SALE` stock movement:

```text
movement_type = 'SALE'
quantity = -quantity_sold
quantity_before = stock_before
quantity_after = stock_after
reference_id = sales.id
```

The sale item must also preserve:

```text
unit_price = selling price at time of sale
unit_cost = cost price at time of sale
```

This guarantees historical financial accuracy.

---

## 6. Stock Workflow

## 6.1 General Stock Logic

Product stock changes only through controlled business events:

- Opening stock
- Restocking
- Sale
- Adjustment

Each stock event must:

- validate the current stock state
- calculate a new stock level
- create a `stock_movements` row
- update the product's `stock_quantity`

## 6.2 Stock Status Logic

A product's status is derived from the live `stock_quantity` and `reorder_level` values.

- **OUT OF STOCK**: `stock_quantity = 0`
- **LOW STOCK**: `stock_quantity > 0` and `stock_quantity <= reorder_level`
- **NORMAL**: `stock_quantity > reorder_level`

This is used for alerts and stock report generation.

---

## 7. Financial Workflow

## 7.1 Sale Finance Logic

For each sale item:

```text
subtotal = unit_price * quantity
profit = (unit_price - unit_cost) * quantity
```

At the sale level:

```text
Revenue = SUM(subtotal)
COGS = SUM(unit_cost * quantity)
Gross Profit = Revenue - COGS
```

The values are stored in the `sales` record and preserved for reporting.

## 7.2 Expense Logic

Expenses are tracked separately from sales:

```text
Total Expenses = SUM(expense.amount)
Net Profit = Gross Profit - Total Expenses
```

## 7.3 Profit Margin Logic

Profit margin is calculated as:

```text
Profit Margin = (Gross Profit / Revenue) × 100
```

If Revenue = 0, Profit Margin is 0% and division by zero must be prevented.

---

## 8. Reporting and Dashboard Architecture

The dashboard and reporting features must read from the database instead of ephemeral in-memory values.

### V1 reporting requirements

- Daily sales summary
- Daily profit report
- Product profitability report
- Stock report
- Low-stock alerts
- Out-of-stock alerts
- Business dashboard showing current KPIs

### Reporting flow

Database records
        ↓
Query layer
        ↓
Aggregation/business calculations
        ↓
Dashboard or report display

This keeps reporting consistent with the actual saved business state.

---

## 9. Rollback Behavior and Error Handling

## 9.1 Transaction Failure

If any critical error happens after the transaction begins:

- DB transaction is rolled back
- Sale is not saved
- Sale items are not saved
- stock quantities are not changed
- stock movement records are not saved

This ensures the system never ends in a partial sale state.

## 9.2 Validation Failure

Validation failures happen before the transaction begins. These errors should not open a database transaction.

Examples:

- empty cart
- invalid quantity
- missing product
- inactive product
- insufficient stock
- unsupported payment method

## 9.3 Operational Rules

- No database operation should silently ignore failure.
- Business errors should surface to the user clearly.
- Critical writes must be done within a transaction boundary.
- The application should log or expose the failed reason for debugging.

---

## 10. Logging Strategy

V1 uses Python's standard `logging` module.

The application should log:

- application startup and shutdown
- successful and failed authentication attempts
- important business operations
- successful and failed sales
- stock adjustments
- backup and restore operations
- unexpected application/database errors

### Logging constraints

- Logs must never contain plaintext passwords, password hashes, or other sensitive authentication data.
- Business data remains in SQLite; logs are for diagnostics and operational troubleshooting, not as a replacement for database records.
- Logs should be concise, structured where practical, and safe for local troubleshooting.

---

## 11. Separation of Concerns

## 11.1 UI vs Business Logic

The UI should only:

- capture user input
- pass data into a service or business function
- display the result or error message

The UI should not:

- directly fire writes to multiple tables
- calculate financial totals without validation
- manipulate stock quantities directly
- create sales rows without transaction handling

## 11.2 Service vs Repository

Business logic should decide what is valid and what must happen, but it should not embed raw SQL when a repository can handle it.

The repository layer should handle:

- queries
- row mapping
- inserting/updating database records
- transaction-aware execution when called by a service

The service layer should handle:

- validation flows
- sale orchestration
- transaction start/commit/rollback
- business error handling

---

## 12. Feature Communication

The major V1 features communicate through a shared database and shared business rules.

### Example communication paths

- Product management → updates product stock and price data
- Sale flow → checks product availability and updates stock
- Stock movement service → writes to `stock_movements`
- Expense module → contributes to net profit reports
- Dashboard/reporting module → reads from `sales`, `sale_items`, `products`, `stock_movements`, and `expenses`

Because all major features rely on the same database and business layer, they remain consistent and auditable.

---

## 13. Reliability Requirements

The architecture must ensure:

- no negative stock
- no partial sales
- complete audit trail
- accurate historical values
- consistent reporting from persisted data
- safe startup and initialization
- predictable database location
- schema versioning / safe initialization

---

## 14. Summary

The V1 architecture is intentionally narrow and reliable:

- SQLite is the database source of truth
- business rules live in the service/business layer
- repositories handle database persistence
- the UI remains focused on user interaction
- sales are atomic and complete or rolled back entirely
- stock changes are always audited with `stock_movements`
- financial reporting is driven by stored records, not UI state
- Python logging supports operational visibility without exposing sensitive data

This architecture is designed to support the frozen V1 requirements without introducing complexity or unapproved features.
