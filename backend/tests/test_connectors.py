import os
import pandas as pd
import pytest
from services.connectors.file_connector import FileConnector
from services.connectors.mock_db_connector import MockDatabaseConnector

def test_file_connector_csv(tmp_path):
    # Create a temporary CSV file
    df = pd.DataFrame({
        "username": ["admin", "user"],
        "role": ["superuser", "viewer"]
    })
    file_path = tmp_path / "test.csv"
    df.to_csv(file_path, index=False)
    
    # Test connector
    connector = FileConnector(str(file_path))
    data = connector.extract_data()
    
    assert len(data) == 2
    assert data[0]["username"] == "admin"
    assert data[1]["role"] == "viewer"

def test_mock_db_connector():
    connector = MockDatabaseConnector("dummy_conn", "SELECT * FROM users")
    data = connector.extract_data()
    
    assert len(data) == 3
    assert data[0]["username"] == "alice_admin"
