from faker import Faker
import pandas as pd
import sqlite3
import random

def generate_synthetic_data(db_path='ecommerce.db', num_records=1000):
    """
    Generates synthetic orders data using Faker and injects intentional 
    data quality issues (duplicates, invalid emails) for demo purposes.
    """
    fake = Faker()
    Faker.seed(42)
    
    customers = []
    for _ in range(num_records):
        email = fake.email()
        # Inject invalid emails
        if random.random() < 0.05:
            email = email.replace('@', '')
            
        customers.append({
            'customer_id': fake.uuid4(),
            'name': fake.name(),
            'email': email,
            'city': fake.city()
        })
        
    # Inject duplicates
    if num_records > 10:
        customers.extend(customers[:10])
        
    df_customers = pd.DataFrame(customers)
    
    # RUN GEMINI AI VALIDATION
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from validation.validate_olist import validate_dataframe
    
    print("Running Gemini AI validation on synthetic_customers...")
    # Validate the tail where we just injected the duplicates
    result = validate_dataframe("synthetic_customers", df_customers.tail(20), sample_size=20)
    
    if result.get("status") != "error":
        score = result.get("quality_score_1_to_10", 10)
        if score < 7:
            # THE HARD STOP
            raise ValueError(f"HARD STOP! Pipeline Halted. Gemini found anomalies: {result.get('issues_found')}")
        else:
            print(f"Validation Passed! Score: {score}/10")
    
    conn = sqlite3.connect(db_path)
    # Prefix tables with synthetic_
    df_customers.to_sql('synthetic_customers', conn, if_exists='replace', index=False)
    conn.close()
    
    print(f"Generated {len(df_customers)} synthetic customers (with ~5% invalid emails and 10 duplicates).")

if __name__ == '__main__':
    generate_synthetic_data()
