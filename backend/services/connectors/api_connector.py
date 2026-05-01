"""REST API / HTTP Connector for fetching data from external APIs"""
import requests
from typing import List, Dict, Any, Optional
from .base import DataConnector


class APIConnector(DataConnector):
    """
    Connector for fetching data from REST APIs.
    """

    def __init__(self, connection_string: str, query: Optional[str] = None):
        super().__init__()
        self.base_url = connection_string.rstrip("/")
        self.session = requests.Session()

    def test_connection(self) -> bool:
        try:
            response = self.session.head(self.base_url, timeout=5)
            return response.status_code < 400
        except Exception as e:
            self.last_error = str(e)
            return False

    def discover_schema(self) -> Dict[str, Any]:
        """
        Fetch the root endpoint to understand the API structure.
        Returns sample keys from the response.
        """
        try:
            response = self.session.get(
                self.base_url,
                headers={"Accept": "application/json", "User-Agent": "GCC-Audit-Agent/1.0"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                sample_keys = list(data[0].keys()) if isinstance(data[0], dict) else []
                return {"type": "list", "sample_keys": sample_keys, "endpoint": self.base_url}
            elif isinstance(data, dict):
                return {"type": "object", "keys": list(data.keys()), "endpoint": self.base_url}
            else:
                return {"type": "unknown", "endpoint": self.base_url}
        except Exception as e:
            self.last_error = f"API discovery error: {str(e)}"
            raise

    def extract_data(self, query_params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Extract data from the API endpoint."""
        try:
            response = self.session.get(
                self.base_url,
                params=query_params,
                headers={"Accept": "application/json", "User-Agent": "GCC-Audit-Agent/1.0"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                for key in ["data", "results", "records", "items", "users"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
            return []
        except Exception as e:
            self.last_error = f"Error fetching from API: {str(e)}"
            raise

    def extract_table(self, table_name: str, columns: List[str] = None, limit: int = 500) -> List[Dict]:
        """For APIs, attempt to hit /{table_name} endpoint."""
        try:
            url = f"{self.base_url}/{table_name}"
            response = self.session.get(
                url,
                headers={"Accept": "application/json", "User-Agent": "GCC-Audit-Agent/1.0"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            records = data if isinstance(data, list) else data.get("data", [data])
            if columns:
                records = [{k: r.get(k) for k in columns} for r in records if isinstance(r, dict)]
            return records[:limit]
        except Exception:
            # Fall back to root endpoint
            return self.extract_data()[:limit]

    def close(self):
        self.session.close()
