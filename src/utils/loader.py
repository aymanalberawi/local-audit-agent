import json
import os

def load_audit_standard(standard_name):
    """Loads the JSON rule-set from the standards folder."""
    # Handle the file path relative to this script
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    file_path = os.path.join(base_path, "standards", f"{standard_name.lower()}.json")
    
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r") as f:
        return json.load(f)