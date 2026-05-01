import json
from src.utils.excel_parser import parse_audit_file
from src.utils.loader import load_audit_standard
from src.utils.ollama_client import get_audit_llm

def run_audit_process(data_path, standard_name):
    """Main logic loop: Data -> Rules -> AI -> Findings."""
    llm = get_audit_llm()
    standard = load_audit_standard(standard_name)
    records = parse_audit_file(data_path)
    
    if not standard or not records:
        return []
    
    findings = []
    for i, record in enumerate(records):
        for control in standard['controls']:
            prompt = f"""
            Identify if this record violates the following rule:
            RULE: {control['logic']}
            DATA: {json.dumps(record)}
            
            Return ONLY a valid JSON: {{"status": "PASS/FAIL", "reason": "short explanation"}}
            """
            try:
                response = llm.invoke(prompt)
                # Cleaning response content in case model adds markdown blocks
                content = response.content.replace('```json', '').replace('```', '').strip()
                result = json.loads(content)
                
                if result.get('status') == 'FAIL':
                    findings.append({
                        "row": i + 1,
                        "control_id": control['id'],
                        "issue": result.get('reason', 'Non-compliant'),
                        "data": str(record)
                    })
            except Exception as e:
                print(f"Error at row {i}: {e}")
                
    return findings