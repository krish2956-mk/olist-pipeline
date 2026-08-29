"""
metrics.py

Pure Python/Pandas calculations that turn raw SQL query results
(from sql_queries.py) into the final KPI numbers shown on the
Executive Dashboard. Kept separate from SQL and chart code so each
metric's business logic is easy to find, test, and reuse.
"""

import pandas as pd


def average_order_value(total_revenue: float, total_orders: int) -> float:
    """Total Revenue / Total Orders."""
    if not total_orders:
        return 0.0
    return round(total_revenue / total_orders, 2)


def repeat_customer_rate(customer_order_counts: pd.DataFrame) -> float:
    """
    % of customers with more than one order.
    customer_order_counts: DataFrame with column 'order_count' (one row per customer).
    """
    if customer_order_counts.empty:
        return 0.0
    total_customers = len(customer_order_counts)
    repeat_customers = (customer_order_counts["order_count"] > 1).sum()
    return round((repeat_customers / total_customers) * 100, 2)


def average_delivery_time_days(delivery_df: pd.DataFrame) -> float:
    """
    Average of (order_delivered_customer_date - order_purchase_timestamp) in days.
    """
    if delivery_df.empty:
        return 0.0
    purchased = pd.to_datetime(delivery_df["order_purchase_timestamp"], errors="coerce")
    delivered = pd.to_datetime(delivery_df["order_delivered_customer_date"], errors="coerce")
    delta_days = (delivered - purchased).dt.total_seconds() / 86400
    delta_days = delta_days.dropna()
    if delta_days.empty:
        return 0.0
    return round(delta_days.mean(), 2)


def late_delivery_percentage(delivery_df: pd.DataFrame) -> float:
    """
    % of delivered orders where order_delivered_customer_date >
    order_estimated_delivery_date, divided by total delivered orders.
    """
    if delivery_df.empty:
        return 0.0
    delivered = pd.to_datetime(delivery_df["order_delivered_customer_date"], errors="coerce")
    estimated = pd.to_datetime(delivery_df["order_estimated_delivery_date"], errors="coerce")
    valid = delivered.notna() & estimated.notna()
    if valid.sum() == 0:
        return 0.0
    late = (delivered[valid] > estimated[valid]).sum()
    return round((late / valid.sum()) * 100, 2)


def average_freight_value(freight_df: pd.DataFrame) -> float:
    """
    Average freight_value across order items.
    NOTE: substitutes for "Average Review Score", which is not available
    because this project has no order_reviews table.
    """
    if freight_df.empty or "freight_value" not in freight_df.columns:
        return 0.0
    return round(freight_df["freight_value"].mean(), 2)


def most_used_payment_method(payment_dist_df: pd.DataFrame) -> str:
    """Payment type with the highest transaction count."""
    if payment_dist_df.empty:
        return "N/A"
    top_row = payment_dist_df.sort_values("transaction_count", ascending=False).iloc[0]
    return str(top_row["payment_type"])


def top_state_by_revenue(revenue_by_state_df: pd.DataFrame) -> tuple:
    """Returns (state, revenue) for the highest-revenue state."""
    if revenue_by_state_df.empty:
        return ("N/A", 0.0)
    top_row = revenue_by_state_df.iloc[0]  # already ordered by revenue DESC in SQL
    return (str(top_row["customer_state"]), float(top_row["total_revenue"]))


def top_seller_by_revenue(revenue_by_seller_df: pd.DataFrame) -> tuple:
    """
    Returns (seller_id, revenue) for the top-earning seller.
    NOTE: substitutes for "Top Product Category", which is not available
    because this project has no products / category translation table.
    """
    if revenue_by_seller_df.empty:
        return ("N/A", 0.0)
    top_row = revenue_by_seller_df.iloc[0]
    return (str(top_row["seller_id"]), float(top_row["total_revenue"]))


def monthly_growth(monthly_revenue_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'growth_pct' column (Month-over-Month % change in revenue)
    to the monthly revenue DataFrame. First month has no prior month,
    so growth is NaN for that row.
    """
    df = monthly_revenue_df.copy()
    if df.empty:
        df["growth_pct"] = []
        return df
    df["growth_pct"] = df["revenue"].pct_change() * 100
    df["growth_pct"] = df["growth_pct"].round(2)
    return df


def latest_month_growth(monthly_revenue_df: pd.DataFrame) -> float:
    """Convenience helper: MoM growth % for the most recent month, or 0.0 if not computable."""
    df = monthly_growth(monthly_revenue_df)
    if df.empty or df["growth_pct"].isna().all():
        return 0.0
    last_val = df["growth_pct"].iloc[-1]
    return 0.0 if pd.isna(last_val) else round(last_val, 2)


def fastest_growing_month(monthly_revenue_df: pd.DataFrame) -> tuple:
    """Returns (month, growth_pct) for the month with the highest MoM growth."""
    df = monthly_growth(monthly_revenue_df).dropna(subset=["growth_pct"])
    if df.empty:
        return ("N/A", 0.0)
    top_row = df.loc[df["growth_pct"].idxmax()]
    return (str(top_row["month"]), float(top_row["growth_pct"]))


def slowest_delivery_state(delivery_df: pd.DataFrame) -> tuple:
    """
    Returns (state, avg_delivery_days) for the state with the highest
    average delivery time. Requires 'customer_state' column in delivery_df.
    """
    if delivery_df.empty or "customer_state" not in delivery_df.columns:
        return ("N/A", 0.0)
    df = delivery_df.copy()
    purchased = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    delivered = pd.to_datetime(df["order_delivered_customer_date"], errors="coerce")
    df["delivery_days"] = (delivered - purchased).dt.total_seconds() / 86400
    df = df.dropna(subset=["delivery_days"])
    if df.empty:
        return ("N/A", 0.0)
    by_state = df.groupby("customer_state")["delivery_days"].mean().sort_values(ascending=False)
    if by_state.empty:
        return ("N/A", 0.0)
    return (str(by_state.index[0]), round(float(by_state.iloc[0]), 2))


def average_customer_spending(total_revenue: float, total_customers: int) -> float:
    """Total Revenue / Total Customers (distinct from AOV, which divides by orders)."""
    if not total_customers:
        return 0.0
    return round(total_revenue / total_customers, 2)
