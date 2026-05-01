import os
import sys

# CRITICAL: Force the root directory into Python's memory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import pandas as pd
from src.agents.orchestrator import run_audit_process

st.set_page_config(page_title="Stratologies Auditor", layout="wide")

st.title("🛡️ Local Compliance Agent")
st.sidebar.title("Configuration")
standard_choice = st.sidebar.selectbox("Standard", ["GDPR_UAE", "ISO27001"])

uploaded_file = st.file_uploader("Upload Evidence", type=["xlsx", "csv"])

if uploaded_file:
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    temp_path = os.path.join(data_dir, uploaded_file.name)
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    if st.button("Run Audit"):
        with st.spinner("Agent analyzing..."):
            results = run_audit_process(temp_path, standard_choice.lower())
            
            if results:
                st.warning(f"Found {len(results)} issues.")
                st.table(results)
            else:
                st.success("No issues found!")