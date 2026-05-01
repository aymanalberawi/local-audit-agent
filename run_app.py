import os
import subprocess
import sys

# Set the PYTHONPATH to the current directory
os.environ["PYTHONPATH"] = os.getcwd()

# Launch Streamlit pointing to the main file
subprocess.run(["streamlit", "run", "web_ui/main.py"])