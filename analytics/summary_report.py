import sqlite3
import pandas as pd
import os

def generate_summary_report(db_path='ecommerce.db', output_path='summary_report.csv'):
    """
    Executes a SQL join across the Olist tables, prints a summary, and exports to CSV.
    """
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Skip report generation.")
        return

    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT 
        c.customer_state,
        COUNT(DISTINCT o.order_id) as total_orders,
        SUM(p.payment_value) as total_revenue
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN payments p ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state
    ORDER BY total_revenue DESC
    LIMIT 10;
    """
    
    try:
        df_summary = pd.read_sql_query(query, conn)
        print("\n--- Top 10 States by Revenue (Olist) ---")
        print(df_summary.to_string(index=False))
        print("----------------------------------------\n")
        
        df_summary.to_csv(output_path, index=False)
        print(f"Summary report exported to {output_path}")
    except Exception as e:
        print(f"Failed to generate summary report: {e}")
        
    conn.close()

if __name__ == '__main__':
    generate_summary_report()
