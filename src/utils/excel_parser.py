import pandas as pd
import os

def parse_audit_file(file_path):
    """Reads Excel/CSV and returns a list of dictionaries."""
    if not os.path.exists(file_path):
        return []
    try:
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Parser Error: {e}")
        return []