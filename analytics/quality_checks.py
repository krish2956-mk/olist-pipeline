"""
Rule-based Data Quality Checks Engine.

Runs a battery of deterministic checks against a DataFrame:
  - Missing Values
  - Duplicate IDs
  - Negative Prices
  - Schema Drift
  - Null Columns (100% empty)
  - Outliers (IQR method)

These are the "hard-coded rules" layer. When a check fails, the result is
handed off to Gemini (see validation/validate_olist.py::explain_quality_issues)
which explains WHY it failed and what likely caused it, in plain English.
"""

import pandas as pd

# Table configs: what "correct" looks like for each known table.
# id_columns   -> column(s) that should be unique (composite key if list)
# price_columns -> numeric columns that should never be negative
# numeric_columns -> columns checked for statistical outliers (IQR method)
# expected_columns -> the canonical schema; anything missing/extra = drift
TABLE_CONFIGS = {
    'customers': {
        'id_columns': ['customer_id'],
        'price_columns': [],
        'numeric_columns': ['customer_zip_code_prefix'],
        'expected_columns': ['customer_id', 'customer_unique_id', 'customer_zip_code_prefix',
                              'customer_city', 'customer_state'],
    },
    'orders': {
        'id_columns': ['order_id'],
        'price_columns': [],
        'numeric_columns': [],
        'expected_columns': ['order_id', 'customer_id', 'order_status', 'order_purchase_timestamp',
                              'order_approved_at', 'order_delivered_carrier_date',
                              'order_delivered_customer_date', 'order_estimated_delivery_date'],
    },
    'items': {
        'id_columns': ['order_id', 'order_item_id'],
        'price_columns': ['price', 'freight_value'],
        'numeric_columns': ['price', 'freight_value'],
        'expected_columns': ['order_id', 'order_item_id', 'product_id', 'seller_id',
                              'shipping_limit_date', 'price', 'freight_value'],
    },
    'payments': {
        'id_columns': ['order_id', 'payment_sequential'],
        'price_columns': ['payment_value'],
        'numeric_columns': ['payment_value', 'payment_installments'],
        'expected_columns': ['order_id', 'payment_sequential', 'payment_type',
                              'payment_installments', 'payment_value'],
    },
    'synthetic_customers': {
        'id_columns': ['customer_id'],
        'price_columns': [],
        'numeric_columns': [],
        'expected_columns': ['customer_id', 'name', 'email', 'city'],
    },
}


def check_missing_values(df):
    """Returns per-column missing counts/percentages for columns that have any nulls."""
    total = len(df)
    if total == 0:
        return {}
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    return {
        col: {'missing_count': int(count), 'missing_pct': round(count / total * 100, 2)}
        for col, count in missing.items()
    }


def check_duplicate_ids(df, id_columns):
    """Checks for duplicate values in the primary key column(s)."""
    if not id_columns or not all(c in df.columns for c in id_columns):
        return {'checked': False, 'duplicate_count': 0}
    dupe_mask = df.duplicated(subset=id_columns, keep=False)
    return {
        'checked': True,
        'id_columns': id_columns,
        'duplicate_count': int(dupe_mask.sum()),
    }


def check_negative_prices(df, price_columns):
    """Checks numeric price/value columns for negative numbers (invalid for e-commerce data)."""
    results = {}
    for col in price_columns or []:
        if col in df.columns:
            numeric_col = pd.to_numeric(df[col], errors='coerce')
            negative_count = int((numeric_col < 0).sum())
            if negative_count > 0:
                results[col] = negative_count
    return results


def check_schema_drift(df, expected_columns):
    """Compares actual columns against the expected schema."""
    if not expected_columns:
        return {'missing_columns': [], 'extra_columns': []}
    actual = set(df.columns)
    expected = set(expected_columns)
    return {
        'missing_columns': sorted(expected - actual),
        'extra_columns': sorted(actual - expected),
    }


def check_null_columns(df):
    """Finds columns that are entirely empty (100% null) — usually a broken source/extract."""
    if len(df) == 0:
        return []
    return [col for col in df.columns if df[col].isnull().all()]


def check_outliers(df, numeric_columns, iqr_multiplier=1.5):
    """Flags statistical outliers per numeric column using the IQR method."""
    results = {}
    for col in numeric_columns or []:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(series) < 4:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - iqr_multiplier * iqr
        upper = q3 + iqr_multiplier * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())
        if outlier_count > 0:
            results[col] = {
                'outlier_count': outlier_count,
                'lower_bound': round(float(lower), 2),
                'upper_bound': round(float(upper), 2),
            }
    return results


def run_quality_checks(df, table_name, thresholds=None):
    """
    Runs the full rule-based data quality battery against a DataFrame.

    Returns a dict with per-check results, a flat list of human-readable
    issue strings, and an overall pass/fail flag.
    """
    thresholds = thresholds or {}
    missing_pct_threshold = thresholds.get('missing_pct_threshold', 5.0)
    outlier_pct_threshold = thresholds.get('outlier_pct_threshold', 10.0)

    config = TABLE_CONFIGS.get(table_name, {})
    total_rows = len(df)

    missing_values = check_missing_values(df)
    duplicate_ids = check_duplicate_ids(df, config.get('id_columns'))
    negative_prices = check_negative_prices(df, config.get('price_columns'))
    schema_drift = check_schema_drift(df, config.get('expected_columns'))
    null_columns = check_null_columns(df)
    outliers = check_outliers(df, config.get('numeric_columns'))

    issues = []

    for col, info in missing_values.items():
        if info['missing_pct'] >= missing_pct_threshold:
            issues.append(f"Column '{col}' has {info['missing_count']} missing values "
                           f"({info['missing_pct']}% of rows)")

    if duplicate_ids.get('duplicate_count', 0) > 0:
        cols = ', '.join(duplicate_ids['id_columns'])
        issues.append(f"Found {duplicate_ids['duplicate_count']} duplicate rows on key column(s): {cols}")

    for col, count in negative_prices.items():
        issues.append(f"Column '{col}' has {count} negative value(s), which is invalid for a price/amount field")

    if schema_drift.get('missing_columns'):
        issues.append(f"Schema drift: missing expected column(s): {schema_drift['missing_columns']}")
    if schema_drift.get('extra_columns'):
        issues.append(f"Schema drift: unexpected new column(s) found: {schema_drift['extra_columns']}")

    if null_columns:
        issues.append(f"Column(s) completely empty (100% null): {null_columns}")

    for col, info in outliers.items():
        outlier_pct = round(info['outlier_count'] / total_rows * 100, 2) if total_rows else 0
        if outlier_pct >= outlier_pct_threshold:
            issues.append(f"Column '{col}' has {info['outlier_count']} statistical outliers "
                           f"({outlier_pct}% of rows, outside [{info['lower_bound']}, {info['upper_bound']}])")

    return {
        'table': table_name,
        'total_rows': total_rows,
        'checks': {
            'missing_values': missing_values,
            'duplicate_ids': duplicate_ids,
            'negative_prices': negative_prices,
            'schema_drift': schema_drift,
            'null_columns': null_columns,
            'outliers': outliers,
        },
        'issues': issues,
        'passed': len(issues) == 0,
    }
