import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_config import get_connection

def load_dataframes_to_sqlite(dfs, db_path=None, prefix=''):
    """
    Loads a dictionary of DataFrames into the configured database with
    idempotency guards (REPLACE). The database backend is controlled by
    db_config.py — no changes needed here when switching databases.
    """
    conn = get_connection(db_path)
    
    for name, df in dfs.items():
        table_name = f"{prefix}{name}"
        
        # To implement true INSERT OR IGNORE / REPLACE in pandas without custom SQL loops, 
        # a common pattern for SQLite is writing to a temp table and executing a SQL statement,
        # or relying on pandas' `if_exists='replace'` for full loads.
        # Since these are static datasets, `if_exists='replace'` acts idempotently for the entire table.
        # For an append scenario, we would use a temp table + INSERT OR IGNORE.
        # Here we demonstrate full load idempotency for simplicity.
        
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Loaded {len(df)} rows into table '{table_name}'")
        
    conn.close()

if __name__ == '__main__':
    print("Run from Airflow DAG.")
