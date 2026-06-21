import sqlite3
import pandas as pd
import re

def is_valid_email(email):
    if pd.isna(email):
        return False
    # Simple regex for email validation
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", str(email)))

def generate_quality_report(db_path='ecommerce.db'):
    """
    Compares the data quality of Olist datasets vs Synthetic datasets side-by-side.
    """
    conn = sqlite3.connect(db_path)
    
    report = []
    
    try:
        # Check Synthetic Data (Expected to have issues)
        df_sync = pd.read_sql("SELECT * FROM synthetic_customers", conn)
        sync_total = len(df_sync)
        sync_dupes = df_sync.duplicated().sum()
        sync_invalid_emails = sync_total - df_sync['email'].apply(is_valid_email).sum()
        
        report.append({
            'Dataset': 'Synthetic Customers',
            'Total Rows': sync_total,
            'Duplicate Rows': sync_dupes,
            'Invalid Emails': sync_invalid_emails
        })
    except Exception as e:
        print("synthetic_customers table not found.")

    try:
        # Check Olist Data (Expected to be cleaner)
        # Olist customers don't have emails, so we'll check something else like missing states
        df_olist = pd.read_sql("SELECT * FROM customers", conn)
        olist_total = len(df_olist)
        olist_dupes = df_olist.duplicated().sum()
        olist_null_states = df_olist['customer_state'].isnull().sum()
        
        report.append({
            'Dataset': 'Olist Customers',
            'Total Rows': olist_total,
            'Duplicate Rows': olist_dupes,
            'Invalid Emails': 'N/A',
            'Null States': olist_null_states
        })
    except Exception as e:
        print("Olist customers table not found.")
        
    conn.close()
    
    if report:
        df_report = pd.DataFrame(report)
        print("\n=== Data Quality Report ===")
        print(df_report.to_string(index=False))
        print("===========================\n")
        df_report.to_csv('data_quality_report.csv', index=False)
        print("Report saved to data_quality_report.csv")

if __name__ == '__main__':
    generate_quality_report()
