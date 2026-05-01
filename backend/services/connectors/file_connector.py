import pandas as pd
from typing import List, Dict, Any
from services.connectors.base import DataConnector


class FileConnector(DataConnector):
    """
    Connector to parse local or uploaded Excel and CSV files.
    """
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def _read_df(self) -> pd.DataFrame:
        if self.file_path.endswith('.csv'):
            return pd.read_csv(self.file_path)
        elif self.file_path.endswith(('.xls', '.xlsx')):
            return pd.read_excel(self.file_path)
        else:
            raise ValueError("Unsupported file format. Please use CSV or Excel.")

    def discover_schema(self) -> Dict[str, Any]:
        """
        Read headers and 3 sample rows without loading the entire file.
        """
        df = self._read_df().head(3)
        df = df.where(pd.notnull(df), None)
        columns = list(df.columns)
        sample_rows = df.to_dict(orient='records')
        return {
            "file": self.file_path,
            "columns": columns,
            "sample_rows": sample_rows
        }

    def extract_data(self) -> List[Dict[str, Any]]:
        df = self._read_df()
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient='records')

    def extract_table(self, table_name: str, columns: List[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        """For files, table_name is ignored; we filter by column names."""
        df = self._read_df()
        df = df.where(pd.notnull(df), None)
        if columns:
            available = [c for c in columns if c in df.columns]
            df = df[available]
        return df.head(limit).to_dict(orient='records')
