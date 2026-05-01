#!/usr/bin/env python3
"""
Test Oracle connection with the corrected C##PORTAL user
"""
import sys
sys.path.insert(0, '/c/local-audit-agent/backend')

from services.connection_tester import test_connection

# Test with Oracle C##PORTAL user
connection_string = "C##PORTAL:portal@nice_moore:1521/?service_name=FREEPDB1"

print("Testing Oracle Connection...")
print(f"Connection String: oracle+oracledb://{connection_string}")
print("-" * 60)

status, message = test_connection("ORACLE", connection_string)

print(f"Status: {status}")
print(f"Message: {message}")
print("-" * 60)

if "ACTIVE" in str(status):
    print("✓ CONNECTION SUCCESSFUL")
    sys.exit(0)
else:
    print("✗ Connection failed")
    sys.exit(1)
