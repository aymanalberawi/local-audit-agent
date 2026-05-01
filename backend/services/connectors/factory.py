"""Factory for creating connector instances based on connection type"""
from typing import Optional
from enum import Enum
from .base import DataConnector
from .file_connector import FileConnector
from .mock_db_connector import MockDatabaseConnector
from .api_connector import APIConnector
from .sql_connector import SQLConnector


class ConnectionType(str, Enum):
    """Enumeration of supported connection types"""
    FILE = "FILE"
    API = "API"
    POSTGRESQL = "POSTGRESQL"
    SQL_SERVER = "SQL_SERVER"
    ORACLE = "ORACLE"
    MOCK_DB = "MOCK_DB"


class ConnectorFactory:
    """Factory for creating data connector instances"""

    @staticmethod
    def create_connector(
        connection_type: str,
        connection_string: str,
        query_or_path: Optional[str] = None
    ) -> DataConnector:
        """
        Create a connector instance based on the connection type

        Args:
            connection_type: Type of connection (FILE, API, POSTGRESQL, SQL_SERVER, ORACLE, MOCK_DB)
            connection_string: Connection string or path specific to the connector type
            query_or_path: Additional parameter (SQL query for databases, path for files)

        Returns:
            A DataConnector subclass instance

        Raises:
            ValueError: If the connection type is not supported
        """
        connection_type = connection_type.upper()

        if connection_type == ConnectionType.FILE.value:
            # For files, connection_string is the file path
            return FileConnector(connection_string)

        elif connection_type == ConnectionType.API.value:
            # For APIs, connection_string is the base URL
            return APIConnector(connection_string, query_or_path)

        elif connection_type == ConnectionType.POSTGRESQL.value:
            query = query_or_path or "SELECT * FROM information_schema.tables"
            return SQLConnector(connection_string, query)

        elif connection_type == ConnectionType.SQL_SERVER.value:
            query = query_or_path or "SELECT * FROM information_schema.tables"
            return SQLConnector(connection_string, query)

        elif connection_type == ConnectionType.ORACLE.value:
            query = query_or_path or "SELECT * FROM all_tables"
            return SQLConnector(connection_string, query)

        elif connection_type == ConnectionType.MOCK_DB.value:
            query = query_or_path or "SELECT * FROM users"
            return MockDatabaseConnector(connection_string, query)

        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

    @staticmethod
    def get_supported_types() -> list:
        """Get list of supported connection types"""
        return [ct.value for ct in ConnectionType]
