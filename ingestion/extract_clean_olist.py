import pandas as pd
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from validation.validate_olist import validate_dataframe

def extract_and_clean_olist(data_dir='.'):
    """
    Extracts the 4 Olist CSVs into DataFrames, performs basic cleaning, and runs AI Validation.
    """
    files = {
        'customers': 'olist_customers_dataset.csv',
        'orders': 'olist_orders_dataset.csv',
        'items': 'olist_order_items_dataset.csv',
        'payments': 'olist_order_payments_dataset.csv'
    }
    
    dfs = {}
    for name, filename in files.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            
            # Basic Cleaning: Drop total duplicates
            df.drop_duplicates(inplace=True)
            
            # Specific cleaning based on dataset
            if name == 'orders':
                # Convert timestamps
                date_cols = ['order_purchase_timestamp', 'order_approved_at', 
                             'order_delivered_carrier_date', 'order_delivered_customer_date', 
                             'order_estimated_delivery_date']
                for col in date_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
            
            if name == 'items':
                if 'shipping_limit_date' in df.columns:
                    df['shipping_limit_date'] = pd.to_datetime(df['shipping_limit_date'], errors='coerce')
            
            # RUN GEMINI AI VALIDATION
            print(f"Running Gemini AI validation on {name}...")
            result = validate_dataframe(name, df)
            if result.get("status") != "error":
                score = result.get("quality_score_1_to_10", 10)
                if score < 7:
                    # THE HARD STOP
                    raise ValueError(f"HARD STOP! {name} failed AI Validation. Score: {score}/10. Issues: {result.get('issues_found')}")
                else:
                    print(f"Validation Passed! Score: {score}/10")
            
            dfs[name] = df
        else:
            print(f"Warning: {filename} not found in {data_dir}")
            
    return dfs

if __name__ == '__main__':
    dfs = extract_and_clean_olist()
    for k, v in dfs.items():
        print(f"Cleaned {k}: {len(v)} rows")
