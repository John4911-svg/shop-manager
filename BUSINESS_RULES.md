# Shop Manager - Business Rules & Formulas

## Overview

This document defines the exact business logic, constraints, and financial calculations that govern Shop Manager V1.

---

## 1. Product Rules

### Product Requirements

- **Product must have a name**: A non-empty string identifying the product.
- **Product must have a unit**: A text field describing the unit of measurement (e.g., "kg", "litre", "piece").
- **Product must have cost price**: Non-negative integer in smallest currency unit; defines the cost to acquire one unit.
- **Product must have selling price**: Non-negative integer in smallest currency unit; defines the price charged to customers.
- **Cost price cannot be invalid**: Must be zero or greater (`cost_price >= 0`).
- **Selling price cannot be invalid**: Must be zero or greater (`selling_price >= 0`).
- **Stock cannot incorrectly become negative**: Inventory quantity must never fall below zero (`stock_quantity >= 0`).

### Product Lifecycle

- **Product can be deactivated**: A product has an `is_active` flag (0 or 1). Deactivated products cannot be added to new sales.
- **Historical sales remain after product deactivation**: Deactivating a product does NOT delete or modify its past sales records. Sales preserve their historical unit prices and unit costs at the time of sale.
- **Only active products can be sold**: When creating a sale, the application must check `is_active = 1` before allowing the product to be added to the cart.

### Product Stock Quantity

- **Product stock quantity**: A product's stock quantity must be a non-negative quantity. A new product may begin with zero stock; if opening stock is provided, it must be recorded through an OPENING stock movement.

### Price History

- **Product prices can change over time**: The `cost_price` and `selling_price` fields in the `products` table are current values. When prices are updated, future sales use the new prices.
- **Historical sales lock in prices**: Each `sale_item` stores `unit_price` (selling price at sale time) and `unit_cost` (cost price at sale time). This ensures that changing a product's current price does NOT retroactively change the revenue, cost, or profit of past sales.

---

## 2. Stock Rules

### Stock Movement Types

Every change to product inventory must create a `stock_movements` record with one of four movement types:

| Movement Type | Description | Effect |
| --- | --- | --- |
| `OPENING` | Initial inventory setup | Increases stock from 0 |
| `RESTOCK` | Inventory replenishment | Increases stock (manual addition) |
| `SALE` | Sale transaction | Decreases stock (automatic) |
| `ADJUSTMENT` | Inventory correction | Increases or decreases stock (manual) |

### Stock Movement Record

Every stock movement must record:
- `product_id`: The product affected.
- `movement_type`: One of the four types above.
- `quantity`: The change amount (positive for additions, negative for reductions); must not be zero.
- `quantity_before`: Stock level before the movement (must be >= 0).
- `quantity_after`: Stock level after the movement (must be >= 0).
- `reference_id`: If movement is caused by a sale, stores the `sales.id`.
- `reason`: Optional explanation for adjustments.
- `created_at`: Timestamp of the movement.

### Stock Change Rules

- **Opening stock increases inventory**: A new product with initial stock 25 creates a `stock_movements` record with `movement_type = 'OPENING'`, `quantity = 25`, `quantity_before = 0`, `quantity_after = 25`.
- **Restocking increases inventory**: When inventory is replenished, create a `RESTOCK` movement.
- **Sale decreases inventory**: When a sale is completed, create a `SALE` movement with a negative quantity, and set `reference_id` to the `sales.id`.
- **Adjustment changes inventory**: Manual inventory corrections (e.g., theft, damage) create an `ADJUSTMENT` movement with a positive or negative quantity and a `reason`.
- **Every stock change creates a movement record**: No stock update to the `products` table is permitted without a corresponding entry in `stock_movements`. Every legitimate stock change creates exactly one corresponding stock movement.
- **Stock cannot become negative**: The application must validate that `quantity_after >= 0` before committing any stock movement.

### Stock Status

A product's stock status is determined as follows:

- **OUT OF STOCK**: `stock_quantity = 0`
- **LOW STOCK**: `stock_quantity > 0` and `stock_quantity <= reorder_level`
- **NORMAL**: `stock_quantity > reorder_level`

---

## 3. Sale Rules

### Sale Validation

- **Cart cannot be empty**: A sale must contain at least one `sale_item`. Attempting to finalize a sale with zero items must fail.
- **Quantity must be positive**: Each item in the sale must have `quantity > 0`. Zero or negative quantities are rejected.
- **Quantity cannot exceed stock**: Before finalizing a sale, the application must verify that the requested quantity for each product does not exceed the current `products.stock_quantity`. If it does, the sale is rejected with an error.

### Sale Calculation

- **Total calculated automatically**: The sale's `total_amount` is the sum of all `sale_items.subtotal` values.
  ```
  total_amount = SUM(sale_item.subtotal for all sale_items in the sale)
  ```

- **Profit calculated automatically**: Each `sale_item.profit` is calculated as:
  ```
  sale_item.profit = (unit_price - unit_cost) * quantity
  ```
  The sale's `gross_profit` is the sum of all `sale_item.profit` values:
  ```
  gross_profit = SUM(sale_item.profit for all sale_items in the sale)
  ```

- **COGS (Cost of Goods Sold) calculated automatically**:
  ```
  total_cost = SUM(unit_cost * quantity for all sale_items in the sale)
  ```

- **Subtotal calculated automatically**:
  ```
  subtotal = SUM(sale_item.subtotal for all sale_items in the sale)
  ```
  where each `sale_item.subtotal = unit_price * quantity`.

### Sale Atomicity

- **Sale saved**: The `sales` record is committed to the database.
- **Sale items saved**: All `sale_item` records for the sale are committed to the database.
- **Stock updated**: The `products.stock_quantity` for each product in the sale is reduced by the sold quantity.
- **Stock movement created**: For each product sold, a `SALE` movement is created with `reference_id = sales.id`.
- **Transaction atomicity**: All four operations (sale, items, stock update, movement) must succeed together. If any operation fails, the entire transaction is rolled back and NO changes are persisted.
- **Sale cannot be reversed in V1**: Once a sale is committed, it cannot be deleted or voided in V1. (Reversal is a future feature in the backlog.)

---

## 4. Financial Rules

### Revenue

- **Revenue calculation defined**: Revenue is the total selling value at the time of the sale.
  ```
  Revenue = total_amount (sum of all sale_item subtotals)
  ```

### Cost of Goods Sold (COGS)

- **COGS calculation defined**: The total cost of all products included in the sale, using the unit cost at the time of sale.
  ```
  COGS = total_cost = SUM(unit_cost * quantity for all sale_items)
  ```

### Gross Profit

- **Gross profit calculation defined**: Revenue minus COGS.
  ```
  Gross Profit = total_amount - total_cost
  ```
  or equivalently:
  ```
  Gross Profit = SUM(sale_item.profit for all sale_items)
  ```

### Profit Margin

- **Profit margin calculation defined**: Gross profit divided by revenue, expressed as a percentage.
  ```
  Profit Margin = (Gross Profit / Revenue) × 100
  ```
  If Revenue = 0, Profit Margin is 0% and division by zero must be prevented.

### Expenses

- **Expense calculation defined**: Expenses are business costs recorded separately from sales (e.g., rent, utilities, wages).
  - Each expense has:
    - `category`: Type of expense (text).
    - `description`: Details of the expense.
    - `amount`: Cost in smallest currency unit (must be > 0).
    - `expense_date`: Date the expense occurred.
    - `notes`: Optional additional information.
  - Expenses are NOT tied to individual sales.

### Net Profit

- **Net profit calculation defined**: Gross profit minus total recorded expenses over a period.
  ```
  Net Profit = Gross Profit - Total Expenses (for a period)
  ```
  where:
  ```
  Total Expenses = SUM(amount for all expenses in the period)
  ```

### Financial Rules

- **All formulas are independent**: Revenue, COGS, and Gross Profit are calculated from the sale data and locked in when the sale is finalized. Changing a product's current price does NOT affect past sales.
- **Monetary values use integers**: All prices and amounts are stored as integers in the smallest currency unit (e.g., cents for USD). Floating-point arithmetic is never used for financial calculations.
- **Negative amounts are not permitted**: Prices, stock quantities, and expenses must be validated at insertion time to prevent data corruption.

---

## 5. Critical Formulas

### Example Scenario

**Product: Rice**
- Cost Price: 8000 (in cents = $80.00)
- Selling Price: 12000 (in cents = $120.00)
- Available Stock: 25 kg

**Sale: S-1001**
- Customer purchases 2 kg of rice at current prices.

### Calculations

1. **Sale Item (rice, 2 kg)**
   ```
   quantity = 2
   unit_price = 12000 (current selling price)
   unit_cost = 8000 (current cost price)
   subtotal = unit_price * quantity = 12000 * 2 = 24000
   profit = (unit_price - unit_cost) * quantity = (12000 - 8000) * 2 = 8000
   ```

2. **Sale Summary**
   ```
   total_amount = subtotal = 24000
   total_cost = unit_cost * quantity = 8000 * 2 = 16000
   gross_profit = total_amount - total_cost = 24000 - 16000 = 8000
   profit_margin = (gross_profit / total_amount) * 100 = (8000 / 24000) * 100 = 33.33%
   ```
   (Or equivalently: `gross_profit = SUM(profit) = 8000`)

3. **Stock Update**
   ```
   Stock before sale: 25 kg
   Quantity sold: 2 kg
   Stock after sale: 25 - 2 = 23 kg
   ```

4. **Stock Movement**
   ```
   movement_type = 'SALE'
   quantity = -2 (negative because stock decreased)
   quantity_before = 25
   quantity_after = 23
   reference_id = 1001 (sales.id)
   created_at = [timestamp of sale]
   ```

5. **Subsequent Expense (same period)**
   ```
   category = "Utilities"
   description = "October electricity bill"
   amount = 50000 (in cents = $500.00)
   expense_date = "2026-10-05"
   ```

6. **Net Profit (for the day)**
   ```
   Gross Profit = 8000 (from sale)
   Expenses = 50000 (utilities)
   Net Profit = 8000 - 50000 = -42000 (loss)
   ```

---

## 6. All Formulas Documented

| Formula | Expression | Purpose |
| --- | --- | --- |
| **Sale Item Subtotal** | `unit_price × quantity` | Revenue from this line item |
| **Sale Item Profit** | `(unit_price − unit_cost) × quantity` | Profit from this line item |
| **Sale Total Amount** | `SUM(sale_item.subtotal)` | Total revenue of the sale |
| **Sale Total Cost** | `SUM(unit_cost × quantity)` | Total cost of goods in the sale |
| **Sale Gross Profit** | `total_amount − total_cost` | Profit before expenses |
| **Profit Margin** | `(gross_profit / total_amount) × 100` | Profitability as percentage |
| **Stock After Sale** | `stock_before − quantity_sold` | Remaining inventory |
| **Total Expenses (Period)** | `SUM(expense.amount)` | All business expenses for a time period |
| **Net Profit (Period)** | `gross_profit − total_expenses` | Bottom-line profit after all costs |

---

## 7. Data Integrity Constraints

### Database-Level Enforcement

All of the following constraints are enforced by SQLite CHECK, UNIQUE, and FOREIGN KEY constraints:

- `users.username` is UNIQUE (no duplicate logins).
- `users.is_active` must be 0 or 1.
- `products.cost_price >= 0`.
- `products.selling_price >= 0`.
- `products.stock_quantity >= 0`.
- `products.reorder_level >= 0`.
- `products.is_active` must be 0 or 1.
- `sale_items.quantity > 0` (strictly positive).
- `sale_items.unit_price >= 0`.
- `sale_items.unit_cost >= 0`.
- `stock_movements.quantity != 0` (never zero).
- `stock_movements.quantity_before >= 0`.
- `stock_movements.quantity_after >= 0`.
- `expenses.amount > 0` (strictly positive).
- Foreign keys link:
  - `products.category_id` → `categories.id`
  - `sale_items.sale_id` → `sales.id`
  - `sale_items.product_id` → `products.id`
  - `stock_movements.product_id` → `products.id`

### Application-Level Validation

The application must validate and enforce:

- A sale cannot be finalized if it contains zero items.
- A product cannot be added to a sale if `is_active = 0`.
- A product cannot be sold if the requested quantity exceeds `stock_quantity`.
- Duplicate prevention of stock movements should be handled through correct transaction and application logic.
- Passwords are hashed before storage (never stored in plain text).

---

## 8. V1 Scope: In & Out

### In Scope (V1)

- Single-user login and basic authentication.
- CRUD operations for products, categories, and expenses.
- Sales cart and sale finalization.
- Stock tracking with movement history.
- **Business Dashboard** with real-time KPIs.
- **Daily Sales and Profit Reports**.
- **Product Profitability Reports**.
- **Stock Reports** (inventory levels, movement history).
- **Low-Stock and Out-of-Stock Alerts**.
- Financial reporting (revenue, COGS, gross profit, net profit, profit margin).
- Local SQLite database.
- Offline operation.
- Data backup capability.

### Out of Scope (Future Versions)

- Multi-user roles and permissions.
- Sale reversals or refunds.
- Payment gateway integration.
- Tax calculations.
- Supplier management.
- Advanced trends and predictive analytics.
- Forecasting.
- Mobile app.
- Cloud synchronization.
- Invoice generation.
- Barcode scanning.

All out-of-scope ideas must be documented in `BACKLOG.md` and will be triaged for future releases after V1 is deployed.

---

## 9. Version Control

**This document is committed to the repository.**

Any changes to business rules must be:
1. Discussed and approved by the project lead.
2. Updated in this file.
3. Committed with a clear message (e.g., "Update: Add reorder level logic").
4. Reflected in code changes.
5. Tested to ensure compliance.

---

## 10. Summary

Shop Manager V1 is a **single-user, offline-first** shop inventory and sales system with:

- ✅ Strict financial integrity (no floating-point, atomic transactions).
- ✅ Complete product lifecycle (creation, pricing, deactivation, historical tracking).
- ✅ Automatic stock management with audit trails.
- ✅ Precise profit calculations (revenue − COGS − expenses − profit margin).
- ✅ Real-time business dashboard and reporting.
- ✅ Low-stock and out-of-stock alerts.
- ✅ Data persistence in a local SQLite database.
- ✅ No partial transactions (all-or-nothing sales).

It is **designed to serve a single shop operator** who needs reliable, accurate financial records, inventory tracking, and business reporting without internet or external services.
