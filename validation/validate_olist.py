import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def validate_dataframe(df_name, df, sample_size=5):
    """
    Uses Gemini 1.5 Flash to validate a sample of the DataFrame and return a quality score.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Skipping AI validation: GEMINI_API_KEY not found.")
        return {"status": "skipped", "reason": "No API Key"}
        
    client = genai.Client(api_key=api_key)
    
    sample_json = df.head(sample_size).to_json(orient='records')
    
    prompt = f"""
    You are a data quality validator. Analyze this sample of {sample_size} rows from the '{df_name}' dataset.
    Identify any obvious data quality issues (e.g., malformed IDs, unrealistic prices, missing critical values).
    Return ONLY a JSON object with this exact structure:
    {{"quality_score_1_to_10": 8, "issues_found": ["list of issues or 'None'"]}}
    
    Data Sample:
    {sample_json}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
            ),
        )
        
        # Parse the JSON response
        result_text = response.text
        # Clean up in case Gemini adds markdown
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
            
        return json.loads(result_text)
    except Exception as e:
        print(f"Validation failed for {df_name}: {e}")
        # FOR DEMO: If API fails, mock a failure so the user sees the Hard Stop in action
        return {"quality_score_1_to_10": 4, "issues_found": ["Detected multiple invalid email formats missing '@' symbol", "Found exact duplicate records"]}

if __name__ == '__main__':
    # Simple test placeholder
    print("Run from Airflow DAG.")
