# Shop Manager - Architecture

## Overview

Shop Manager V1 is a single-user, offline-first desktop/web application built around a local SQLite database. It is designed to manage products, inventory, sales, expenses, and business reporting without requiring network access or a remote service.

The system is intentionally simple, reliable, and auditable. Every important business action must be stored in the database and must be consistent with the frozen V1 business rules.

---

## 1. Architectural Principles

### 1.1 Offline-first

- The application runs locally and stores all business data in SQLite.
- There is no dependency on a remote database or online payment system.
- Data persists after application shutdown and restart.

### 1.2 Single responsibility by layer

The system is separated into clear layers:

- UI layer: user interaction and display
- Business logic layer: validation, calculations, rules, workflows
- Data access layer: database read/write operations
- SQLite database layer: tables, constraints, indexes, transactions

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

The UI layer does not own business rules. It may call business logic, but it must not directly mutate the database for critical business operations.

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
- controlling the sale transaction workflow
- protecting historical prices and data consistency

This layer sits between the UI and database access layer.

### Business logic responsibilities

- Validate a sale before transaction starts
- Confirm product exists and is active
- Confirm quantity is valid and available in stock
- Verify payment method is valid
- Compute sale item totals and sale totals
- Decide stock updates for each product
- Create stock movement entries for approved inventory changes
- Generate dashboard/report aggregates from database records

---

## 2.3 Data Access Layer

Responsible for:

- database connection management
- SQL execution
- schema creation and migration awareness
- CRUD operations for tables
- transaction control
- querying business data for reports and dashboards

The data access layer should isolate SQL details from business logic.

### Responsibilities

- open/close SQLite connection
- prepare SQL inserts/updates/selects
- run transactions
- read products, sales, expenses, stock movements
- return database records in a business-friendly format

---

## 2.4 Database Layer

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

The business logic should call these methods rather than writing SQL directly.

This keeps the database access layer stable and reduces duplication.

---

## 5. Transaction Boundary

The most critical architectural rule in V1 is the transaction boundary around a sale.

### Transaction Start Condition

A sale transaction begins only after all validations pass.

### Required validations before transaction start

- Cart is not empty
- Every product exists
- Every product is active
- Every quantity is greater than 0
- Quantity requested does not exceed available stock
- Selling price and cost price are available for each item
- Payment method is valid
- Sale totals can be computed without error

### Transaction operations

Inside the transaction, the system must perform these steps together:

1. Create the `sales` row
2. Create each `sale_items` row
3. Update each `products.stock_quantity`
4. Create corresponding `stock_movements` records of type `SALE`
5. Compute and store `sales.subtotal`, `sales.total_amount`, `sales.total_cost`, and `sales.gross_profit`
6. Commit transaction

### Rollback condition

If any step fails after the transaction begins:

- SQL error occurs
- stock validation fails unexpectedly
- data cannot be inserted or updated consistently
- stock movement cannot be created
- any business rule is violated

Then:

- rollback transaction
- no sale record remains
- no sale items remain
- no stock changes remain
- no stock movement remains

This atomicity protects the integrity of the entire sales process.

---

## 6. Sale Workflow

## 6.1 End-to-End Flow

User finalizes cart
        ↓
Validate sale
        ↓
BEGIN DATABASE TRANSACTION
        ↓
Create sales record
        ↓
Create sale_items records
        ↓
Update product stock quantities
        ↓
Create SALE stock_movements
        ↓
Calculate/store sale totals and gross profit
        ↓
COMMIT TRANSACTION
        ↓
Sale successfully completed

## 6.2 Validation Workflow

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

## 6.3 Stock Update Workflow

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

## 7. Stock Workflow

## 7.1 General Stock Logic

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

## 7.2 Stock Status Logic

A product's status is derived from the live `stock_quantity` and `reorder_level` values.

- **OUT OF STOCK**: `stock_quantity = 0`
- **LOW STOCK**: `stock_quantity > 0` and `stock_quantity <= reorder_level`
- **NORMAL**: `stock_quantity > reorder_level`

This is used for alerts and stock report generation.

---

## 8. Financial Workflow

## 8.1 Sale Finance Logic

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

## 8.2 Expense Logic

Expenses are tracked separately from sales:

```text
Total Expenses = SUM(expense.amount)
Net Profit = Gross Profit - Total Expenses
```

## 8.3 Profit Margin Logic

Profit margin is calculated as:

```text
Profit Margin = (Gross Profit / Revenue) × 100
```

If Revenue = 0, Profit Margin is 0% and division by zero must be prevented.

---

## 9. Reporting and Dashboard Architecture

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

## 10. Rollback Behavior and Error Handling

## 10.1 Transaction Failure

If any critical error happens after the transaction begins:

- DB transaction is rolled back
- Sale is not saved
- Sale items are not saved
- stock quantities are not changed
- stock movement records are not saved

This ensures the system never ends in a partial sale state.

## 10.2 Validation Failure

Validation failures happen before the transaction begins. These errors should not open a database transaction.

Examples:

- empty cart
- invalid quantity
- missing product
- inactive product
- insufficient stock
- unsupported payment method

## 10.3 Operational Rules

- No database operation should silently ignore failure.
- Business errors should surface to the user clearly.
- Critical writes must be done within a transaction boundary.
- The application should log or expose the failed reason for debugging.

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

## 11.2 Business Logic vs Database Access

Business logic should decide what is valid and what must happen, but it should not embed raw SQL when a data access layer can handle it.

The data access layer should handle:

- queries
- row mapping
- inserting/updating database records
- transaction execution

Business logic should handle:

- validation rules
- sale calculation rules
- stock status rules
- reporting calculations
- rollback triggers

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
- business rules live in a business logic layer
- database access is isolated behind a data layer
- the UI remains focused on user interaction
- sales are atomic and complete or rolled back entirely
- stock changes are always audited with `stock_movements`
- financial reporting is driven by stored records, not UI state

This architecture is designed to support the frozen V1 requirements without introducing complexity or unapproved features.
