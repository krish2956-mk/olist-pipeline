import requests
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_config import get_connection
import json
import pandas as pd
from datetime import datetime

def extract_and_load_weather(db_path=None):
    """
    Fetches live weather data from Open-Meteo, adds an ingested_at timestamp,
    stores the raw JSON, and saves to the configured database.
    """
    # Example: Weather in Sao Paulo (matching Olist geography roughly)
    url = "https://api.open-meteo.com/v1/forecast?latitude=-23.5505&longitude=-46.6333&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        # Enterprise Pattern: Keep the raw JSON payload for replayability
        raw_payload = json.dumps(data)
        ingested_at = datetime.utcnow().isoformat()
        
        # Parse current weather into a structured format
        current = data.get('current', {})
        structured_data = {
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'temperature_2m': current.get('temperature_2m'),
            'wind_speed_10m': current.get('wind_speed_10m'),
            'ingested_at': ingested_at,
            'raw_json': raw_payload
        }
        
        df = pd.DataFrame([structured_data])
        
        conn = get_connection(db_path)
        # Append mode for time-series data
        df.to_sql('weather_data', conn, if_exists='append', index=False)
        conn.close()
        
        print(f"Weather data ingested successfully at {ingested_at}")
    else:
        print(f"Failed to fetch weather data. Status code: {response.status_code}")

if __name__ == '__main__':
    extract_and_load_weather()
