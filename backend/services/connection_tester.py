"""Service for testing data source connections"""
import os
import requests
from sqlalchemy import create_engine, text
from models.hierarchy import ConnectionStatus

def test_connection(connection_type: str, connection_string: str) -> tuple[str, str]:
    """
    Test a connection and return (status, message)

    Returns:
        tuple: (ConnectionStatus, status_message)
    """
    try:
        if connection_type == "FILE":
            return test_file_connection(connection_string)
        elif connection_type == "API":
            return test_api_connection(connection_string)
        elif connection_type in ["POSTGRESQL", "SQL_SERVER", "ORACLE"]:
            return test_database_connection(connection_type, connection_string)
        elif connection_type == "MOCK_DB":
            # Mock DB always succeeds
            return ConnectionStatus.ACTIVE, "Mock database connection successful"
        else:
            return ConnectionStatus.FAILED, f"Unknown connection type: {connection_type}"
    except Exception as e:
        return ConnectionStatus.FAILED, str(e)


def test_file_connection(connection_string: str) -> tuple[str, str]:
    """Test if a file connection is valid"""
    try:
        # For FILE connections, we just validate the format
        # The actual file will be provided during audit creation

        # If connection_string is empty or None, that's ok for FILE type
        # (file will be uploaded or provided per-audit)
        if not connection_string or connection_string.strip() == "":
            return ConnectionStatus.ACTIVE, "File connection ready (file will be provided at audit time)"

        # If a path is provided, check if it exists and is readable
        if os.path.exists(connection_string):
            # Check if file is readable
            if not os.access(connection_string, os.R_OK):
                return ConnectionStatus.FAILED, f"File is not readable: {connection_string}"

            # Check file size
            file_size = os.path.getsize(connection_string)
            if file_size == 0:
                return ConnectionStatus.FAILED, f"File is empty: {connection_string}"

            return ConnectionStatus.ACTIVE, f"File connection successful ({file_size} bytes)"
        else:
            # File doesn't exist yet, but that's ok - user can upload file during audit
            return ConnectionStatus.ACTIVE, f"File connection ready (file path: {connection_string})"
    except Exception as e:
        return ConnectionStatus.FAILED, f"File error: {str(e)}"


def test_api_connection(connection_string: str) -> tuple[str, str]:
    """Test if an API endpoint is reachable"""
    try:
        # Validate URL format
        if not connection_string.startswith(("http://", "https://")):
            return ConnectionStatus.FAILED, "API URL must start with http:// or https://"

        # Test the connection with a simple GET request
        response = requests.head(connection_string, timeout=5, verify=False)

        if response.status_code < 400:
            return ConnectionStatus.ACTIVE, f"API connection successful (HTTP {response.status_code})"
        else:
            return ConnectionStatus.FAILED, f"API returned error: HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return ConnectionStatus.FAILED, "API connection timed out"
    except requests.exceptions.ConnectionError:
        return ConnectionStatus.FAILED, "API connection refused or unreachable"
    except Exception as e:
        return ConnectionStatus.FAILED, f"API error: {str(e)}"


def test_database_connection(db_type: str, connection_string: str) -> tuple[str, str]:
    """Test database connection"""
    try:
        # Build SQLAlchemy connection string
        if db_type == "POSTGRESQL":
            # connection_string should be: postgresql+psycopg2://user:password@host:port/database
            if not connection_string.startswith("postgresql"):
                # Try to parse simple format: user:password@host:port/database
                connection_string = f"postgresql+psycopg2://{connection_string}"
        elif db_type == "SQL_SERVER":
            # connection_string should be: mssql+pyodbc://user:password@host/database?driver=ODBC+Driver+17+for+SQL+Server
            if not connection_string.startswith("mssql"):
                connection_string = f"mssql+pyodbc://{connection_string}?driver=ODBC+Driver+17+for+SQL+Server"
        elif db_type == "ORACLE":
            # connection_string should be: oracle+oracledb://user:password@host:port/?service_name=dbname
            if not connection_string.startswith("oracle"):
                connection_string = f"oracle+oracledb://{connection_string}"

        # Try to create a connection (with timeout)
        # Set timeout based on database type
        connect_args = {}
        if db_type == "POSTGRESQL":
            connect_args = {"connect_timeout": 5}
        elif db_type == "SQL_SERVER":
            connect_args = {"timeout": 5}
        # Note: oracledb doesn't support timeout in connect_args

        engine = create_engine(
            connection_string,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=False
        )

        # Test the connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.close()

        return ConnectionStatus.ACTIVE, f"{db_type} connection successful"
    except Exception as e:
        error_msg = str(e)
        # Truncate long error messages
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        return ConnectionStatus.FAILED, f"{db_type} error: {error_msg}"
