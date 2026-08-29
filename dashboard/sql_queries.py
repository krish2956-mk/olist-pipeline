"""
sql_queries.py

All SQL query definitions for the Executive Business Analytics Dashboard.

Design notes:
- Every query is "filter-aware": it accepts a `filters` dict (date range,
  customer state, payment type, order status) built from the sidebar and
  applies it via a single reusable `filtered_orders` CTE.
- Aggregation happens in SQL wherever possible (per the performance
  requirement) instead of loading entire tables into Pandas.
- Only tables that actually exist in `ecommerce.db` are used:
  customers, orders, items, payments. There is no products, order_reviews,
  or product_category_name_translation table in this project, so any KPI
  that depends on them (review score, product category) is intentionally
  NOT implemented here — see executive_dashboard.py for the documented
  substitutions (freight value in place of review score, seller revenue in
  place of product category).
"""

import pandas as pd


# ──────────────────────────────────────────────────────────────────────────
# Shared filter clause
# ──────────────────────────────────────────────────────────────────────────
def _filtered_orders_cte(filters):
    """
    Builds a single reusable `filtered_orders` CTE that encodes every
    sidebar filter (date range, state, payment type, order status).
    All other queries in this module build on top of this CTE so the
    filter logic lives in exactly one place.

    filters: dict with keys
        start_date (str 'YYYY-MM-DD'), end_date (str 'YYYY-MM-DD'),
        states (list[str] or empty), payment_types (list[str] or empty),
        order_statuses (list[str] or empty)

    Returns: (cte_sql: str, params: list)
    """
    clauses = ["o.order_purchase_timestamp BETWEEN ? AND ?"]
    params = [filters["start_date"], filters["end_date"]]

    if filters.get("states"):
        placeholders = ",".join(["?"] * len(filters["states"]))
        clauses.append(f"c.customer_state IN ({placeholders})")
        params.extend(filters["states"])

    if filters.get("order_statuses"):
        placeholders = ",".join(["?"] * len(filters["order_statuses"]))
        clauses.append(f"o.order_status IN ({placeholders})")
        params.extend(filters["order_statuses"])

    if filters.get("payment_types"):
        placeholders = ",".join(["?"] * len(filters["payment_types"]))
        clauses.append(
            f"o.order_id IN (SELECT order_id FROM payments WHERE payment_type IN ({placeholders}))"
        )
        params.extend(filters["payment_types"])

    where_sql = " AND ".join(clauses)

    cte_sql = f"""
    WITH filtered_orders AS (
        SELECT
            o.order_id,
            o.customer_id,
            c.customer_unique_id,
            c.customer_state,
            o.order_status,
            o.order_purchase_timestamp,
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE {where_sql}
    )
    """
    return cte_sql, params


# ──────────────────────────────────────────────────────────────────────────
# Sidebar filter option lookups (unfiltered — used to populate widgets)
# ──────────────────────────────────────────────────────────────────────────
def get_filter_options(conn):
    """Returns distinct values for each sidebar filter and the overall date bounds."""
    states = pd.read_sql_query(
        "SELECT DISTINCT customer_state FROM customers WHERE customer_state IS NOT NULL ORDER BY customer_state",
        conn,
    )["customer_state"].tolist()

    payment_types = pd.read_sql_query(
        "SELECT DISTINCT payment_type FROM payments WHERE payment_type IS NOT NULL ORDER BY payment_type",
        conn,
    )["payment_type"].tolist()

    order_statuses = pd.read_sql_query(
        "SELECT DISTINCT order_status FROM orders WHERE order_status IS NOT NULL ORDER BY order_status",
        conn,
    )["order_status"].tolist()

    bounds = pd.read_sql_query(
        "SELECT MIN(order_purchase_timestamp) AS min_d, MAX(order_purchase_timestamp) AS max_d FROM orders",
        conn,
    )

    return {
        "states": states,
        "payment_types": payment_types,
        "order_statuses": order_statuses,
        "min_date": bounds["min_d"].iloc[0],
        "max_date": bounds["max_d"].iloc[0],
    }


# ──────────────────────────────────────────────────────────────────────────
# Core KPIs
# ──────────────────────────────────────────────────────────────────────────
def get_core_kpis(conn, filters):
    """Total Revenue, Total Orders, Total Customers — computed in a single SQL pass."""
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + """
        SELECT
            COUNT(DISTINCT fo.order_id) AS total_orders,
            COUNT(DISTINCT fo.customer_unique_id) AS total_customers,
            COALESCE(SUM(p.payment_value), 0) AS total_revenue
        FROM filtered_orders fo
        JOIN payments p ON p.order_id = fo.order_id
    """
    return pd.read_sql_query(query, conn, params=params)


def get_customer_order_counts(conn, filters):
    """One row per customer_unique_id with their order count — feeds Repeat Customer Rate."""
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + """
        SELECT customer_unique_id, COUNT(DISTINCT order_id) AS order_count
        FROM filtered_orders
        GROUP BY customer_unique_id
    """
    return pd.read_sql_query(query, conn, params=params)


def get_delivery_data(conn, filters):
    """
    Raw purchase/delivered/estimated timestamps for delivered orders.
    Used to derive Average Delivery Time, Late Delivery %, and the
    Delivery Time Distribution box plot — all from one query.
    """
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + """
        SELECT
            order_id,
            customer_state,
            order_purchase_timestamp,
            order_delivered_customer_date,
            order_estimated_delivery_date
        FROM filtered_orders
        WHERE order_status = 'delivered'
          AND order_delivered_customer_date IS NOT NULL
    """
    return pd.read_sql_query(query, conn, params=params)


def get_freight_values(conn, filters):
    """
    Freight value per order item within the filtered order set.
    Used for Average Freight Value (substitute for unavailable Review
    Score) and the Freight Value Distribution histogram.
    """
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + """
        SELECT i.freight_value
        FROM filtered_orders fo
        JOIN items i ON i.order_id = fo.order_id
        WHERE i.freight_value IS NOT NULL
    """
    return pd.read_sql_query(query, conn, params=params)


def get_payment_distribution(conn, filters):
    """Transaction count and revenue by payment_type — feeds Most Used Payment Method + pie chart."""
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + """
        SELECT
            p.payment_type,
            COUNT(*) AS transaction_count,
            SUM(p.payment_value) AS total_value
        FROM filtered_orders fo
        JOIN payments p ON p.order_id = fo.order_id
        GROUP BY p.payment_type
        ORDER BY total_value DESC
    """
    return pd.read_sql_query(query, conn, params=params)


def get_revenue_by_state(conn, filters):
    """Revenue and order count per customer_state — feeds Top State KPI + horizontal bar chart."""
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + """
        SELECT
            fo.customer_state,
            COUNT(DISTINCT fo.order_id) AS total_orders,
            SUM(p.payment_value) AS total_revenue
        FROM filtered_orders fo
        JOIN payments p ON p.order_id = fo.order_id
        GROUP BY fo.customer_state
        ORDER BY total_revenue DESC
    """
    return pd.read_sql_query(query, conn, params=params)


def get_revenue_by_seller(conn, filters, top_n=10):
    """
    Revenue by seller_id (top N) — this project has no products table, so
    seller performance is used as the closest available substitute for
    "Top Product Category".
    """
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + f"""
        SELECT
            i.seller_id,
            SUM(i.price) AS total_revenue,
            COUNT(*) AS items_sold
        FROM filtered_orders fo
        JOIN items i ON i.order_id = fo.order_id
        GROUP BY i.seller_id
        ORDER BY total_revenue DESC
        LIMIT {top_n}
    """
    return pd.read_sql_query(query, conn, params=params)


def get_monthly_revenue(conn, filters):
    """Revenue grouped by purchase month — feeds Monthly Revenue Trend + MoM Growth %."""
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + """
        SELECT
            SUBSTRING(CAST(fo.order_purchase_timestamp AS TEXT), 1, 7) AS month,
            SUM(p.payment_value) AS revenue
        FROM filtered_orders fo
        JOIN payments p ON p.order_id = fo.order_id
        GROUP BY month
        ORDER BY month
    """
    return pd.read_sql_query(query, conn, params=params)


def get_order_status_distribution(conn, filters):
    """Order count per order_status — feeds the donut chart."""
    cte_sql, params = _filtered_orders_cte(filters)
    query = cte_sql + """
        SELECT order_status, COUNT(*) AS count
        FROM filtered_orders
        GROUP BY order_status
        ORDER BY count DESC
    """
    return pd.read_sql_query(query, conn, params=params)
