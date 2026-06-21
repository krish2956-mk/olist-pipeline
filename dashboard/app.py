import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
import re
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Olist Data Pipeline Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark glassmorphism background */
.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.1);
}

/* Metric cards */
div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.4);
}

/* Headings */
h1, h2, h3 {
    color: #ffffff !important;
}

/* Section headers */
.section-header {
    font-size: 1.2rem;
    font-weight: 600;
    color: rgba(255,255,255,0.9);
    padding: 8px 0 4px 0;
    border-bottom: 2px solid rgba(139, 92, 246, 0.5);
    margin-bottom: 16px;
}

/* Hero banner */
.hero {
    background: linear-gradient(135deg, rgba(139,92,246,0.3), rgba(59,130,246,0.3));
    border: 1px solid rgba(139,92,246,0.4);
    border-radius: 20px;
    padding: 30px 40px;
    margin-bottom: 30px;
    backdrop-filter: blur(10px);
}
.hero h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 6px 0;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero p {
    color: rgba(255,255,255,0.65);
    margin: 0;
    font-size: 0.95rem;
}

/* Badge pill */
.badge {
    display: inline-block;
    background: rgba(139,92,246,0.25);
    color: #a78bfa;
    border: 1px solid rgba(139,92,246,0.4);
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 6px;
}

/* Data quality highlight card */
.quality-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
}

/* DataFrames */
div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.1);
}

/* Tabs */
button[data-baseweb="tab"] {
    color: rgba(255,255,255,0.6) !important;
    font-weight: 500;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #a78bfa !important;
    border-bottom: 2px solid #a78bfa !important;
}

/* Divider */
hr {
    border-color: rgba(255,255,255,0.1);
}

/* Status dot */
.dot-green { color: #34d399; }
.dot-red   { color: #f87171; }
</style>
""", unsafe_allow_html=True)

# ── Database Helper ───────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ecommerce.db')

@st.cache_data(ttl=300)
def query(sql):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Query failed: {e}")
        return pd.DataFrame()

def is_valid_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", str(email))) if pd.notna(email) else False

# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all():
    revenue_by_state = query("""
        SELECT c.customer_state,
               COUNT(DISTINCT o.order_id) as total_orders,
               ROUND(SUM(p.payment_value), 2) as total_revenue
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN payments p ON o.order_id = p.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_state
        ORDER BY total_revenue DESC
    """)
    order_status = query("""
        SELECT order_status, COUNT(*) as count
        FROM orders
        GROUP BY order_status
        ORDER BY count DESC
    """)
    payment_types = query("""
        SELECT payment_type, COUNT(*) as count,
               ROUND(SUM(payment_value), 2) as total_value
        FROM payments
        GROUP BY payment_type
        ORDER BY total_value DESC
    """)
    monthly_orders = query("""
        SELECT strftime('%Y-%m', order_purchase_timestamp) as month,
               COUNT(*) as orders,
               ROUND(SUM(p.payment_value),2) as revenue
        FROM orders o
        JOIN payments p ON o.order_id = p.order_id
        WHERE order_purchase_timestamp IS NOT NULL
          AND strftime('%Y', order_purchase_timestamp) >= '2017'
        GROUP BY month
        ORDER BY month
    """)
    top_items = query("""
        SELECT seller_id,
               COUNT(*) as items_sold,
               ROUND(SUM(price), 2) as revenue
        FROM items
        GROUP BY seller_id
        ORDER BY revenue DESC
        LIMIT 10
    """)
    synthetic_customers = query("SELECT * FROM synthetic_customers")
    weather = query("""
        SELECT * FROM weather_data
        ORDER BY ingested_at DESC
        LIMIT 10
    """)
    return revenue_by_state, order_status, payment_types, monthly_orders, top_items, synthetic_customers, weather

# ── Plotly theme ──────────────────────────────────────────────────────────────
TEMPLATE = "plotly_dark"
COLOR_SEQ = px.colors.qualitative.Bold
PRIMARY = "#a78bfa"
ACCENT  = "#60a5fa"

# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔧 Pipeline Dashboard")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["📦 Overview", "🗺️ Revenue by State", "📈 Order Trends",
         "💳 Payments", "🧪 Data Quality", "🌤️ Weather Feed",
         "📤 Upload Data"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("""
    **Stack**  
    <span class="badge">Python</span>
    <span class="badge">Pandas</span>  
    <span class="badge">SQLite</span>
    <span class="badge">Airflow</span>  
    <span class="badge">Gemini</span>
    <span class="badge">Streamlit</span>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
revenue_by_state, order_status, payment_types, monthly_orders, top_items, synthetic_customers, weather = load_all()

# ──────────────────────────────────────────────────────────────────────────────
# OVERVIEW
# ──────────────────────────────────────────────────────────────────────────────
if page == "📦 Overview":
    st.markdown("""
    <div class="hero">
        <h1>📦 Olist Data Pipeline</h1>
        <p>End-to-end data engineering project · 3 sources · Gemini AI Validation · SQLite · Airflow orchestration</p>
    </div>
    """, unsafe_allow_html=True)

    # KPI Row
    total_orders    = query("SELECT COUNT(*) as c FROM orders")["c"].iloc[0]
    total_customers = query("SELECT COUNT(DISTINCT customer_id) as c FROM customers")["c"].iloc[0]
    total_revenue   = query("SELECT ROUND(SUM(payment_value),2) as r FROM payments")["r"].iloc[0]
    total_sellers   = query("SELECT COUNT(DISTINCT seller_id) as c FROM items")["c"].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🛒 Total Orders",    f"{total_orders:,}")
    c2.metric("👤 Unique Customers", f"{total_customers:,}")
    c3.metric("💰 Total Revenue",   f"R$ {total_revenue:,.0f}")
    c4.metric("🏪 Unique Sellers",  f"{total_sellers:,}")

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">Order Status Breakdown</div>', unsafe_allow_html=True)
        if not order_status.empty:
            fig = px.pie(order_status, names='order_status', values='count',
                         template=TEMPLATE, color_discrete_sequence=COLOR_SEQ, hole=0.45)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              legend_font_color='white', margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Top 10 States by Revenue</div>', unsafe_allow_html=True)
        if not revenue_by_state.empty:
            fig = px.bar(revenue_by_state.head(10), x='customer_state', y='total_revenue',
                         template=TEMPLATE, color='total_revenue',
                         color_continuous_scale='Purples',
                         labels={'total_revenue': 'Revenue (R$)', 'customer_state': 'State'})
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              coloraxis_showscale=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Monthly Revenue Trend</div>', unsafe_allow_html=True)
    if not monthly_orders.empty:
        fig = px.area(monthly_orders, x='month', y='revenue',
                      template=TEMPLATE, color_discrete_sequence=[PRIMARY])
        fig.update_traces(fill='tozeroy', fillcolor='rgba(167,139,250,0.15)', line_color=PRIMARY)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis_tickangle=-45, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# REVENUE BY STATE
# ──────────────────────────────────────────────────────────────────────────────
elif page == "🗺️ Revenue by State":
    st.markdown("## 🗺️ Revenue by State")
    if not revenue_by_state.empty:
        fig = px.bar(revenue_by_state, x='customer_state', y='total_revenue',
                     color='total_orders', template=TEMPLATE,
                     color_continuous_scale='Viridis',
                     labels={'total_revenue': 'Revenue (R$)', 'customer_state': 'State', 'total_orders': 'Orders'},
                     title='Total Revenue and Orders per Brazilian State')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.scatter(revenue_by_state, x='total_orders', y='total_revenue',
                              text='customer_state', template=TEMPLATE,
                              color='total_revenue', color_continuous_scale='Purples',
                              title='Orders vs Revenue (Bubble per State)',
                              labels={'total_orders': 'Orders', 'total_revenue': 'Revenue (R$)'})
            fig2.update_traces(textposition='top center', marker_size=12)
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.markdown('<div class="section-header">Full State Breakdown Table</div>', unsafe_allow_html=True)
            st.dataframe(
                revenue_by_state.style
                    .format({'total_revenue': 'R$ {:,.2f}', 'total_orders': '{:,}'}),
                use_container_width=True, height=400
            )

# ──────────────────────────────────────────────────────────────────────────────
# ORDER TRENDS
# ──────────────────────────────────────────────────────────────────────────────
elif page == "📈 Order Trends":
    st.markdown("## 📈 Order Trends")
    if not monthly_orders.empty:
        fig = px.line(monthly_orders, x='month', y='orders',
                      template=TEMPLATE, color_discrete_sequence=[ACCENT],
                      title='Monthly Order Volume',
                      labels={'month': 'Month', 'orders': 'Orders'})
        fig.update_traces(line_width=2.5)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.area(monthly_orders, x='month', y='revenue',
                           template=TEMPLATE, color_discrete_sequence=[PRIMARY],
                           title='Monthly Revenue (R$)')
            fig2.update_traces(fill='tozeroy', fillcolor='rgba(167,139,250,0.15)')
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            fig3 = px.bar(order_status, x='order_status', y='count',
                          template=TEMPLATE, color='order_status',
                          color_discrete_sequence=COLOR_SEQ,
                          title='Orders by Status',
                          labels={'order_status': 'Status', 'count': 'Count'})
            fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# PAYMENTS
# ──────────────────────────────────────────────────────────────────────────────
elif page == "💳 Payments":
    st.markdown("## 💳 Payment Analysis")
    if not payment_types.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(payment_types, names='payment_type', values='total_value',
                         template=TEMPLATE, color_discrete_sequence=COLOR_SEQ, hole=0.4,
                         title='Revenue by Payment Type')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              legend_font_color='white')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig2 = px.bar(payment_types, x='payment_type', y='count',
                          template=TEMPLATE, color='payment_type',
                          color_discrete_sequence=COLOR_SEQ,
                          title='Number of Transactions by Payment Type',
                          labels={'payment_type': 'Type', 'count': 'Transactions'})
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown('<div class="section-header">Payment Summary Table</div>', unsafe_allow_html=True)
        st.dataframe(
            payment_types.style.format({'total_value': 'R$ {:,.2f}', 'count': '{:,}'}),
            use_container_width=True
        )

# ──────────────────────────────────────────────────────────────────────────────
# DATA QUALITY
# ──────────────────────────────────────────────────────────────────────────────
elif page == "🧪 Data Quality":
    st.markdown("## 🧪 Data Quality Report")
    st.markdown("Olist real data vs Faker-generated synthetic data — side by side.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">✅ Olist Customers (Real Data)</div>', unsafe_allow_html=True)
        olist_df = query("SELECT * FROM customers")
        olist_total = len(olist_df)
        olist_dupes = olist_df.duplicated().sum()
        olist_nulls = olist_df['customer_state'].isnull().sum()
        st.metric("Total Rows",       f"{olist_total:,}")
        st.metric("Duplicate Rows",   f"{olist_dupes:,}")
        st.metric("Null States",       f"{olist_nulls:,}")

        olist_error_rate = ((olist_dupes + olist_nulls) / olist_total) * 100 if olist_total > 0 else 0
        olist_score = max(0.0, 10.0 - (olist_error_rate * 1.0))
        olist_color = "#34d399" if olist_score >= 8.0 else "#f87171"

        st.markdown(f"""
        <div class="quality-card">
            <strong>Quality Score: </strong>
            <span style="color:{olist_color}; font-size:1.4rem; font-weight:700;">{olist_score:.1f} / 10</span><br>
            <small style="color:rgba(255,255,255,0.5);">Deducts 1 point per 1% error rate (Duplicates + Nulls)</small>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-header">⚠️ Synthetic Customers (Faker Data)</div>', unsafe_allow_html=True)
        syn_total  = len(synthetic_customers)
        syn_dupes  = synthetic_customers.duplicated().sum()
        if 'email' in synthetic_customers.columns:
            syn_bad_email = syn_total - synthetic_customers['email'].apply(is_valid_email).sum()
        else:
            syn_bad_email = 0
        st.metric("Total Rows",       f"{syn_total:,}")
        st.metric("Duplicate Rows",   f"{syn_dupes:,}", delta=f"+{syn_dupes} ⬆", delta_color="inverse")
        st.metric("Invalid Emails",   f"{syn_bad_email:,}", delta=f"+{syn_bad_email} ⬆", delta_color="inverse")

        syn_error_rate = ((syn_dupes + syn_bad_email) / syn_total) * 100 if syn_total > 0 else 0
        syn_score = max(0.0, 10.0 - (syn_error_rate * 1.0))
        syn_color = "#34d399" if syn_score >= 8.0 else "#f87171"

        st.markdown(f"""
        <div class="quality-card">
            <strong>Quality Score: </strong>
            <span style="color:{syn_color}; font-size:1.4rem; font-weight:700;">{syn_score:.1f} / 10</span><br>
            <small style="color:rgba(255,255,255,0.5);">Deducts 1 point per 1% error rate (Duplicates + Invalid Emails)</small>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">Synthetic Data Preview</div>', unsafe_allow_html=True)
    st.dataframe(synthetic_customers.head(20), use_container_width=True)

    # Bar comparison chart
    compare_df = pd.DataFrame({
        'Dataset': ['Olist Customers', 'Synthetic Customers'],
        'Duplicates': [int(olist_dupes), int(syn_dupes)],
        'Invalid Emails / Nulls': [int(olist_nulls), int(syn_bad_email)],
    })
    compare_melted = compare_df.melt(id_vars='Dataset', var_name='Issue', value_name='Count')
    fig = px.bar(compare_melted, x='Dataset', y='Count', color='Issue',
                 barmode='group', template=TEMPLATE, color_discrete_sequence=[PRIMARY, ACCENT],
                 title='Data Quality Issues: Olist vs Synthetic')
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# WEATHER FEED
# ──────────────────────────────────────────────────────────────────────────────
elif page == "🌤️ Weather Feed":
    st.markdown("## 🌤️ Live Weather Feed")
    st.markdown("Real-time weather data ingested from the [Open-Meteo API](https://open-meteo.com/) — Sao Paulo, Brazil.")

    if not weather.empty:
        col1, col2, col3 = st.columns(3)
        latest = weather.iloc[0]
        col1.metric("🌡️ Temperature", f"{latest.get('temperature_2m', 'N/A')} °C")
        col2.metric("💨 Wind Speed",  f"{latest.get('wind_speed_10m', 'N/A')} km/h")
        col3.metric("📍 Location",     "São Paulo, BR")

        st.markdown('<div class="section-header">Ingestion Log</div>', unsafe_allow_html=True)
        display_cols = [c for c in weather.columns if c != 'raw_json']
        st.dataframe(weather[display_cols], use_container_width=True)

        with st.expander("🔍 View Raw JSON Payload (last record)"):
            st.code(latest.get('raw_json', '{}'), language='json')
    else:
        st.warning("No weather data found. Run `python ingestion/extract_weather.py` first.")

# ──────────────────────────────────────────────────────────────────────────────
# UPLOAD DATA
# ──────────────────────────────────────────────────────────────────────────────
elif page == "📤 Upload Data":
    st.markdown("## 📤 Upload Your Own Data")
    st.markdown("""
    Upload **4 CSV files** that match the Olist schema. The pipeline will:
    1. Read and clean your data with Pandas
    2. Run **Gemini AI validation** on each file  
    3. Load them into the database if the quality score is **7 or above**
    4. Refresh all dashboard charts instantly
    """)

    EXPECTED_SCHEMAS = {
        'customers': ['customer_id', 'customer_unique_id', 'customer_zip_code_prefix', 'customer_city', 'customer_state'],
        'orders':    ['order_id', 'customer_id', 'order_status', 'order_purchase_timestamp'],
        'items':     ['order_id', 'order_item_id', 'product_id', 'seller_id', 'price', 'freight_value'],
        'payments':  ['order_id', 'payment_sequential', 'payment_type', 'payment_installments', 'payment_value'],
    }

    st.markdown("---")
    st.markdown('<div class="section-header">Step 1 — Upload Your 4 CSV Files</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        f_customers = st.file_uploader("Customers CSV",  type='csv', key='up_customers',
                                       help=f"Required columns: {', '.join(EXPECTED_SCHEMAS['customers'])}")
        f_orders    = st.file_uploader("Orders CSV",     type='csv', key='up_orders',
                                       help=f"Required columns: {', '.join(EXPECTED_SCHEMAS['orders'])}")
    with col2:
        f_items     = st.file_uploader("Order Items CSV", type='csv', key='up_items',
                                       help=f"Required columns: {', '.join(EXPECTED_SCHEMAS['items'])}")
        f_payments  = st.file_uploader("Payments CSV",   type='csv', key='up_payments',
                                       help=f"Required columns: {', '.join(EXPECTED_SCHEMAS['payments'])}")

    all_uploaded = all([f_customers, f_orders, f_items, f_payments])

    # Show schema reference
    with st.expander("View Required Column Schemas"):
        for name, cols in EXPECTED_SCHEMAS.items():
            st.markdown(f"**{name}:** `{'`, `'.join(cols)}`")

    st.markdown("---")
    st.markdown('<div class="section-header">Step 2 — Validate and Ingest</div>', unsafe_allow_html=True)

    if not all_uploaded:
        st.info("Please upload all 4 CSV files above to enable ingestion.")
    else:
        st.success("All 4 files uploaded! Click the button below to validate and ingest.")
        if st.button("Run Gemini Validation and Load into Database", type="primary"):
            files_map = {
                'customers': f_customers,
                'orders':    f_orders,
                'items':     f_items,
                'payments':  f_payments,
            }

            # Import validation
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from validation.validate_olist import validate_dataframe

            results_log = []
            all_passed  = True
            validated_dfs = {}

            progress = st.progress(0, text="Starting validation...")

            for i, (name, uploaded_file) in enumerate(files_map.items()):
                progress.progress((i) * 25, text=f"Validating '{name}'...")

                df = pd.read_csv(uploaded_file)

                # Schema Check
                expected = EXPECTED_SCHEMAS[name]
                missing_cols = [c for c in expected if c not in df.columns]
                if missing_cols:
                    results_log.append({'Dataset': name, 'Score': 'N/A',
                                        'Status': 'SCHEMA ERROR',
                                        'Issues': f"Missing columns: {missing_cols}"})
                    all_passed = False
                    continue

                # Clean timestamps for orders
                if name == 'orders':
                    for col in df.columns:
                        if 'timestamp' in col or 'date' in col:
                            df[col] = pd.to_datetime(df[col], errors='coerce')

                # Deduplicate
                before = len(df)
                df.drop_duplicates(inplace=True)
                dupes_removed = before - len(df)

                # Gemini Validation
                result = validate_dataframe(name, df)
                score  = result.get('quality_score_1_to_10', 0)
                issues = result.get('issues_found', [])
                passed = score >= 7

                if not passed:
                    all_passed = False

                results_log.append({
                    'Dataset':         name,
                    'Rows':            len(df),
                    'Dupes Removed':   dupes_removed,
                    'Score':           f"{score}/10",
                    'Status':          'PASSED' if passed else 'FAILED',
                    'Issues':          ', '.join(issues) if issues else 'None'
                })
                validated_dfs[name] = df

            progress.progress(100, text="Validation complete!")

            # Show Validation Results
            st.markdown('<div class="section-header">Gemini Validation Results</div>', unsafe_allow_html=True)
            results_df = pd.DataFrame(results_log)
            st.dataframe(results_df, use_container_width=True)

            if all_passed:
                st.success("All datasets passed Gemini AI Validation! Loading into database...")
                conn = sqlite3.connect(DB_PATH)
                for name, df in validated_dfs.items():
                    df.to_sql(name, conn, if_exists='replace', index=False)
                    st.markdown(f"Loaded **{len(df):,} rows** into table `{name}`")
                conn.close()

                st.cache_data.clear()
                st.balloons()
                st.success("Database updated! Navigate to any page to see your new data in the charts.")
            else:
                failed = [r['Dataset'] for r in results_log if r['Status'] == 'FAILED']
                st.error(
                    f"HARD STOP — The following datasets failed Gemini AI Validation and were NOT loaded: {', '.join(failed)}. "
                    "Please fix the data quality issues listed above and re-upload."
                )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:rgba(255,255,255,0.3); font-size:0.8rem; padding: 10px 0;">
    Built with Python · Pandas · SQLite · Apache Airflow · Gemini API · Streamlit
</div>
""", unsafe_allow_html=True)
