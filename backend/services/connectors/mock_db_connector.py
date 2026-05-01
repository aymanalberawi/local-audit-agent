from typing import List, Dict, Any
from services.connectors.base import DataConnector


MOCK_SCHEMA = {
    "tables": [
        {
            "name": "users",
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "username", "type": "varchar"},
                {"name": "email", "type": "varchar"},
                {"name": "role", "type": "varchar"},
                {"name": "department", "type": "varchar"},
                {"name": "last_login", "type": "timestamp"},
            ]
        },
        {
            "name": "access_logs",
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "user_id", "type": "integer"},
                {"name": "action", "type": "varchar"},
                {"name": "timestamp", "type": "timestamp"},
                {"name": "ip_address", "type": "varchar"},
            ]
        }
    ]
}

MOCK_DATA = {
    "users": [
        {"id": 1, "username": "alice_admin", "email": "alice@company.com", "role": "admin", "department": "Marketing", "last_login": "2026-04-25T10:00:00Z"},
        {"id": 2, "username": "bob_user",    "email": "bob@company.com",   "role": "user",  "department": "IT",        "last_login": "2026-04-20T08:30:00Z"},
        {"id": 3, "username": "charlie_svc", "email": "SECRET_ID_7782",    "role": "system","department": "IT",        "last_login": "2026-01-01T00:00:00Z"},
        {"id": 4, "username": "jane_smith",  "email": "jane@company.com",  "role": "admin", "department": "Marketing", "last_login": "2026-04-27T09:00:00Z"},
    ],
    "access_logs": [
        {"id": 1, "user_id": 1, "action": "LOGIN",  "timestamp": "2026-04-25T10:00:00Z", "ip_address": "192.168.1.10"},
        {"id": 2, "user_id": 3, "action": "DELETE", "timestamp": "2026-04-25T11:00:00Z", "ip_address": "10.0.0.5"},
    ]
}


class MockDatabaseConnector(DataConnector):
    """
    A mock database connector for testing without a real database.
    Simulates a company HR/IAM database with users and access logs.
    """
    def __init__(self, connection_string: str, query: str = ""):
        super().__init__()
        self.connection_string = connection_string
        self.query = query

    def discover_schema(self) -> Dict[str, Any]:
        """Return the mock schema without fetching row data."""
        return MOCK_SCHEMA

    def extract_data(self) -> List[Dict[str, Any]]:
        """Return all mock users (backward compatibility)."""
        return MOCK_DATA["users"]

    def extract_table(self, table_name: str, columns: List[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        """Extract records from a specific mock table."""
        data = MOCK_DATA.get(table_name, [])
        if columns:
            data = [{k: r[k] for k in columns if k in r} for r in data]
        return data[:limit]
