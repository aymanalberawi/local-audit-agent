from abc import ABC, abstractmethod
from typing import List, Dict, Any


class DataConnector(ABC):
    """
    Abstract Base Class for all data connectors.
    Every connector must implement:
      - extract_data()      → full dataset fetch
      - discover_schema()   → lightweight structural introspection (no row data)
    """

    def __init__(self):
        self.last_error: str = None

    @abstractmethod
    def extract_data(self) -> List[Dict[str, Any]]:
        """Extract all data from the source"""
        pass

    @abstractmethod
    def discover_schema(self) -> Dict[str, Any]:
        """
        Introspect the data source structure without fetching data.
        Returns a dict describing what datasets are available.
        
        For SQL:  {"tables": [{"name": "users", "columns": ["id","email","role"]}]}
        For API:  {"endpoints": ["/users", "/roles"], "sample_keys": ["id","name"]}
        For File: {"columns": ["id","email","role"], "sample_rows": [{...}, {...}]}
        """
        pass

    def extract_table(self, table_name: str, columns: List[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Extract records from a specific table/dataset.
        Subclasses should override this for targeted extraction.
        Falls back to extract_data() if not overridden.
        """
        return self.extract_data()

    def test_connection(self) -> bool:
        """Test if the connection is valid."""
        try:
            self.discover_schema()
            return True
        except Exception as e:
            self.last_error = str(e)
            return False
