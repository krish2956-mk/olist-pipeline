"""
charts.py

Reusable Plotly chart builders for the Executive Business Analytics
Dashboard. Every function takes a DataFrame (already produced by
sql_queries.py) and returns a ready-to-render `go.Figure` / `px` figure,
styled to match the dark glassmorphism theme used in dashboard/app.py.
"""

import plotly.express as px
import plotly.graph_objects as go

TEMPLATE = "plotly_dark"
COLOR_SEQ = px.colors.qualitative.Bold
PRIMARY = "#a78bfa"
ACCENT = "#60a5fa"
POSITIVE = "#34d399"
NEGATIVE = "#f87171"


def _transparent(fig, **layout_kwargs):
    """Applies the shared transparent-background styling used across app.py."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="rgba(255,255,255,0.85)",
        margin=dict(t=40, b=20, l=10, r=10),
        **layout_kwargs,
    )
    return fig


def revenue_by_state_bar(df):
    """Horizontal bar chart: Revenue by State."""
    if df.empty:
        return go.Figure()
    df_sorted = df.sort_values("total_revenue", ascending=True)
    fig = px.bar(
        df_sorted,
        x="total_revenue",
        y="customer_state",
        orientation="h",
        template=TEMPLATE,
        color="total_revenue",
        color_continuous_scale="Purples",
        labels={"total_revenue": "Revenue (R$)", "customer_state": "State"},
        title="Revenue by State",
    )
    fig.update_layout(coloraxis_showscale=False)
    return _transparent(fig)


def revenue_by_seller_bar(df):
    """
    Horizontal bar chart: Revenue by Seller.
    Substitutes for "Revenue by Product Category" since this project has
    no products / category translation table.
    """
    if df.empty:
        return go.Figure()
    df_sorted = df.sort_values("total_revenue", ascending=True)
    # Shorten seller_id for readability on the y-axis
    df_sorted = df_sorted.assign(seller_label=df_sorted["seller_id"].str[:8] + "…")
    fig = px.bar(
        df_sorted,
        x="total_revenue",
        y="seller_label",
        orientation="h",
        template=TEMPLATE,
        color="total_revenue",
        color_continuous_scale="Blues",
        labels={"total_revenue": "Revenue (R$)", "seller_label": "Seller"},
        title="Top 10 Sellers by Revenue",
    )
    fig.update_layout(coloraxis_showscale=False)
    return _transparent(fig)


def monthly_revenue_line(df):
    """Line chart: Monthly Revenue Trend."""
    if df.empty:
        return go.Figure()
    fig = px.line(
        df,
        x="month",
        y="revenue",
        template=TEMPLATE,
        color_discrete_sequence=[PRIMARY],
        markers=True,
        labels={"month": "Month", "revenue": "Revenue (R$)"},
        title="Monthly Revenue Trend",
    )
    fig.update_traces(line_width=2.5)
    fig.update_layout(xaxis_tickangle=-45)
    return _transparent(fig)


def payment_method_pie(df):
    """Pie chart: Payment Method Distribution (by transaction count)."""
    if df.empty:
        return go.Figure()
    fig = px.pie(
        df,
        names="payment_type",
        values="transaction_count",
        template=TEMPLATE,
        color_discrete_sequence=COLOR_SEQ,
        hole=0.35,
        title="Payment Method Distribution",
    )
    fig.update_layout(legend_font_color="white")
    return _transparent(fig)


def order_status_donut(df):
    """Donut chart: Order Status Distribution."""
    if df.empty:
        return go.Figure()
    fig = px.pie(
        df,
        names="order_status",
        values="count",
        template=TEMPLATE,
        color_discrete_sequence=COLOR_SEQ,
        hole=0.55,
        title="Order Status Distribution",
    )
    fig.update_layout(legend_font_color="white")
    return _transparent(fig)


def freight_value_histogram(df):
    """
    Histogram: Freight Value Distribution.
    Substitutes for "Review Score Distribution" since this project has no
    order_reviews table.
    """
    if df.empty or "freight_value" not in df.columns:
        return go.Figure()
    fig = px.histogram(
        df,
        x="freight_value",
        nbins=40,
        template=TEMPLATE,
        color_discrete_sequence=[ACCENT],
        labels={"freight_value": "Freight Value (R$)"},
        title="Freight Value Distribution",
    )
    return _transparent(fig)


def delivery_time_box(delivery_df):
    """
    Box plot: Delivery Time Distribution (days), grouped by customer_state
    if available, otherwise a single overall box.
    """
    if delivery_df.empty:
        return go.Figure()
    df = delivery_df.copy()
    import pandas as pd
    purchased = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    delivered = pd.to_datetime(df["order_delivered_customer_date"], errors="coerce")
    df["delivery_days"] = (delivered - purchased).dt.total_seconds() / 86400
    df = df.dropna(subset=["delivery_days"])
    if df.empty:
        return go.Figure()

    fig = px.box(
        df,
        y="delivery_days",
        template=TEMPLATE,
        color_discrete_sequence=[PRIMARY],
        points=False,
        labels={"delivery_days": "Delivery Time (days)"},
        title="Delivery Time Distribution",
    )
    return _transparent(fig)


def monthly_growth_bar(growth_df):
    """
    Bar chart: Month-over-Month Revenue Growth %.
    Colors positive growth green, negative growth red.
    """
    if growth_df.empty:
        return go.Figure()
    df = growth_df.dropna(subset=["growth_pct"])
    if df.empty:
        return go.Figure()
    colors = [POSITIVE if v >= 0 else NEGATIVE for v in df["growth_pct"]]
    fig = go.Figure(
        go.Bar(x=df["month"], y=df["growth_pct"], marker_color=colors)
    )
    fig.update_layout(
        title="Month-over-Month Revenue Growth %",
        xaxis_title="Month",
        yaxis_title="Growth (%)",
        template=TEMPLATE,
        xaxis_tickangle=-45,
    )
    return _transparent(fig)
