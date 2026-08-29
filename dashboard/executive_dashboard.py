"""
executive_dashboard.py

Executive Business Analytics Dashboard page. This EXTENDS the existing
Streamlit app (dashboard/app.py) — it does not replace or modify any
existing page. app.py imports `render()` from this module and calls it
when the user selects "Executive Dashboard" in the sidebar.

Data availability note
-----------------------
This project's SQLite database only contains: customers, orders, items,
payments (plus weather_data and synthetic_customers, which are unrelated
to business analytics). There is NO order_reviews, products, or
product_category_name_translation table anywhere in the project.

Per the "only use real data, never fabricate metrics" requirement, two
KPIs/charts from the original spec are substituted with the closest real
equivalent, and two filters are dropped:

    Requested (unavailable)          -> Used instead
    --------------------------------------------------------------
    Average Review Score             -> Average Freight Value
    Top Product Category             -> Top Seller by Revenue
    Review Score Distribution        -> Freight Value Distribution
    Product Category filter          -> (dropped, no products table)
    Review Score filter              -> (dropped, no reviews table)
    "Best product category" insight  -> "Best performing seller" insight
"""

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from db_config import get_connection
from dashboard import sql_queries as q
from dashboard import metrics as m
from dashboard import charts as c


# ──────────────────────────────────────────────────────────────────────────
# Cached data access layer
# ──────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _load_filter_options(db_path):
    conn = get_connection(db_path)
    try:
        return q.get_filter_options(conn)
    finally:
        conn.close()


@st.cache_data(ttl=300, show_spinner=False)
def _load_dashboard_data(db_path, filters_key):
    """
    filters_key is a hashable tuple representation of the filters dict so
    Streamlit's cache can key on it correctly (dicts/lists aren't hashable).
    Loads every query this page needs in one cached call so switching
    filters only re-runs SQL once per change, not once per widget.
    """
    filters = dict(filters_key)
    # Lists were flattened into tuples for hashing; expand them back.
    filters["states"] = list(filters.get("states") or [])
    filters["payment_types"] = list(filters.get("payment_types") or [])
    filters["order_statuses"] = list(filters.get("order_statuses") or [])

    conn = get_connection(db_path)
    try:
        data = {
            "core_kpis": q.get_core_kpis(conn, filters),
            "customer_order_counts": q.get_customer_order_counts(conn, filters),
            "delivery": q.get_delivery_data(conn, filters),
            "freight": q.get_freight_values(conn, filters),
            "payment_dist": q.get_payment_distribution(conn, filters),
            "revenue_by_state": q.get_revenue_by_state(conn, filters),
            "revenue_by_seller": q.get_revenue_by_seller(conn, filters, top_n=10),
            "monthly_revenue": q.get_monthly_revenue(conn, filters),
            "order_status_dist": q.get_order_status_distribution(conn, filters),
        }
    finally:
        conn.close()
    return data


def _filters_to_key(filters):
    """Converts the filters dict into a hashable tuple-of-tuples for caching."""
    return tuple(
        (k, tuple(v) if isinstance(v, list) else v) for k, v in sorted(filters.items())
    )


# ──────────────────────────────────────────────────────────────────────────
# Sidebar filters
# ──────────────────────────────────────────────────────────────────────────
def _render_filters(options):
    """Renders the sidebar filter widgets and returns the filters dict."""
    st.sidebar.markdown("### 🔎 Executive Dashboard Filters")

    min_date = pd.to_datetime(options["min_date"]).date() if options["min_date"] else datetime(2016, 1, 1).date()
    max_date = pd.to_datetime(options["max_date"]).date() if options["max_date"] else datetime.now().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="exec_date_range",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    states = st.sidebar.multiselect(
        "Customer State", options=options["states"], default=[], key="exec_states"
    )
    payment_types = st.sidebar.multiselect(
        "Payment Method", options=options["payment_types"], default=[], key="exec_payment_types"
    )
    order_statuses = st.sidebar.multiselect(
        "Order Status", options=options["order_statuses"], default=[], key="exec_order_statuses"
    )

    st.sidebar.caption(
        "Product Category and Review Score filters are not available — "
        "this dataset has no products or order_reviews table."
    )

    return {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "states": states,
        "payment_types": payment_types,
        "order_statuses": order_statuses,
    }


# ──────────────────────────────────────────────────────────────────────────
# KPI card helpers
# ──────────────────────────────────────────────────────────────────────────
def _kpi_row(columns_data):
    """columns_data: list of (label, value, help_text_or_None)."""
    cols = st.columns(len(columns_data))
    for col, (label, value, help_text) in zip(cols, columns_data):
        col.metric(label, value, help=help_text)


# ──────────────────────────────────────────────────────────────────────────
# Business Insights panel
# ──────────────────────────────────────────────────────────────────────────
def _render_insights(data):
    st.markdown('<div class="section-header">💡 Business Insights</div>', unsafe_allow_html=True)

    core = data["core_kpis"].iloc[0]
    total_revenue = float(core["total_revenue"] or 0)
    total_customers = int(core["total_customers"] or 0)

    top_state, top_state_rev = m.top_state_by_revenue(data["revenue_by_state"])
    fastest_month, fastest_growth = m.fastest_growing_month(data["monthly_revenue"])
    slow_state, slow_days = m.slowest_delivery_state(data["delivery"])
    top_seller, top_seller_rev = m.top_seller_by_revenue(data["revenue_by_seller"])
    top_payment = m.most_used_payment_method(data["payment_dist"])
    avg_spend = m.average_customer_spending(total_revenue, total_customers)
    repeat_rate = m.repeat_customer_rate(data["customer_order_counts"])

    insights = [
        f"📍 **Highest revenue state:** {top_state} (R$ {top_state_rev:,.2f})",
        f"📈 **Fastest growing month:** {fastest_month} ({fastest_growth:+.2f}% MoM)",
        f"🐢 **Slowest delivery state:** {slow_state} (~{slow_days:.1f} days on average)",
        f"🏪 **Best performing seller:** {top_seller[:12]}… (R$ {top_seller_rev:,.2f} in revenue)"
        f" — _substitute for 'best product category', no products table available_",
        f"💳 **Most common payment method:** {top_payment}",
        f"💰 **Average customer spending:** R$ {avg_spend:,.2f}",
        f"🔁 **Repeat customer percentage:** {repeat_rate:.2f}%",
    ]

    for line in insights:
        st.markdown(f"- {line}")


# ──────────────────────────────────────────────────────────────────────────
# Main render entrypoint (called from app.py)
# ──────────────────────────────────────────────────────────────────────────
def render(db_path):
    """Renders the full Executive Dashboard page. Call from app.py's page router."""
    st.markdown("""
    <div class="hero">
        <h1>📊 Executive Dashboard</h1>
        <p>Business KPIs computed live from SQL over the Olist tables · filters apply to every card and chart below</p>
    </div>
    """, unsafe_allow_html=True)

    if not os.path.exists(db_path):
        st.warning("Database not found. Load data via the Upload Data page first.")
        return

    options = _load_filter_options(db_path)
    filters = _render_filters(options)
    data = _load_dashboard_data(db_path, _filters_to_key(filters))

    core = data["core_kpis"].iloc[0]
    total_revenue = float(core["total_revenue"] or 0)
    total_orders = int(core["total_orders"] or 0)
    total_customers = int(core["total_customers"] or 0)

    if total_orders == 0:
        st.info("No orders match the current filter selection. Try widening the date range or clearing filters.")
        return

    aov = m.average_order_value(total_revenue, total_orders)
    repeat_rate = m.repeat_customer_rate(data["customer_order_counts"])
    avg_delivery_days = m.average_delivery_time_days(data["delivery"])
    late_pct = m.late_delivery_percentage(data["delivery"])
    avg_freight = m.average_freight_value(data["freight"])
    top_payment = m.most_used_payment_method(data["payment_dist"])
    top_state, top_state_rev = m.top_state_by_revenue(data["revenue_by_state"])
    top_seller, top_seller_rev = m.top_seller_by_revenue(data["revenue_by_seller"])
    mom_growth = m.latest_month_growth(data["monthly_revenue"])

    # ── Row 1: Revenue, Orders, Customers, AOV ──────────────────────────
    st.markdown('<div class="section-header">Top Row — Core Volume KPIs</div>', unsafe_allow_html=True)
    _kpi_row([
        ("💰 Total Revenue", f"R$ {total_revenue:,.0f}", None),
        ("🛒 Total Orders", f"{total_orders:,}", None),
        ("👤 Total Customers", f"{total_customers:,}", "Distinct customer_unique_id"),
        ("🧾 Avg Order Value", f"R$ {aov:,.2f}", None),
    ])

    # ── Row 2: Repeat rate, Delivery time, Late %, Freight (review substitute) ─
    st.markdown('<div class="section-header">Second Row — Fulfillment & Loyalty</div>', unsafe_allow_html=True)
    _kpi_row([
        ("🔁 Repeat Customer Rate", f"{repeat_rate:.2f}%", None),
        ("🚚 Avg Delivery Time", f"{avg_delivery_days:.1f} days", None),
        ("⏰ Late Delivery %", f"{late_pct:.2f}%", "Delivered after the estimated delivery date"),
        ("📦 Avg Freight Value", f"R$ {avg_freight:,.2f}", "Substitute for review score — no reviews table in this dataset"),
    ])

    # ── Row 3: Top state, Top seller, Payment method, MoM growth ───────
    st.markdown('<div class="section-header">Third Row — Mix & Trend</div>', unsafe_allow_html=True)
    _kpi_row([
        ("🗺️ Top State", f"{top_state}", f"R$ {top_state_rev:,.2f} in revenue"),
        ("🏪 Top Seller", f"{top_seller[:10]}…", f"R$ {top_seller_rev:,.2f} — substitute for product category"),
        ("💳 Top Payment Method", f"{top_payment}", None),
        ("📈 Latest MoM Growth", f"{mom_growth:+.2f}%", None),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Interactive Charts</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(c.revenue_by_state_bar(data["revenue_by_state"]), use_container_width=True)
    with col2:
        st.plotly_chart(c.revenue_by_seller_bar(data["revenue_by_seller"]), use_container_width=True)

    st.plotly_chart(c.monthly_revenue_line(data["monthly_revenue"]), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(c.payment_method_pie(data["payment_dist"]), use_container_width=True)
    with col4:
        st.plotly_chart(c.order_status_donut(data["order_status_dist"]), use_container_width=True)

    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(c.freight_value_histogram(data["freight"]), use_container_width=True)
    with col6:
        st.plotly_chart(c.delivery_time_box(data["delivery"]), use_container_width=True)

    growth_df = m.monthly_growth(data["monthly_revenue"])
    st.plotly_chart(c.monthly_growth_bar(growth_df), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Business Insights panel ─────────────────────────────────────────
    _render_insights(data)
