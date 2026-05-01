"""SQL Database Connector for PostgreSQL, SQL Server, and Oracle"""
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy import create_engine, text
from .base import DataConnector

logger = logging.getLogger(__name__)


class SQLConnector(DataConnector):
    """
    Connector for SQL databases. Supports PostgreSQL, SQL Server, Oracle.
    """

    def __init__(self, connection_string: str, query: str = "SELECT 1"):
        super().__init__()
        self.query = query
        self.last_error = None
        self.error_code = None
        try:
            self.engine = create_engine(connection_string, pool_pre_ping=True)
            self.connection_string = connection_string
            # Detect DB type
            if "postgresql" in connection_string:
                self.db_type = "POSTGRESQL"
            elif "mssql" in connection_string:
                self.db_type = "SQL_SERVER"
            elif "oracle" in connection_string:
                self.db_type = "ORACLE"
            else:
                self.db_type = "UNKNOWN"
        except ImportError as e:
            self.error_code = "ERR_DRIVER_NOT_INSTALLED"
            self.last_error = f"[{self.error_code}] Database driver not installed: {str(e)}"
            logger.error(f"Driver not installed: {str(e)}")
            self.engine = None
            self.db_type = "UNKNOWN"
        except Exception as e:
            error_str = str(e)
            # Categorize the error
            if "invalid connection option" in error_str.lower():
                self.error_code = "ERR_INVALID_CONNECTION_STRING"
            elif "could not translate host name" in error_str.lower():
                self.error_code = "ERR_HOST_NOT_FOUND"
            elif "connection refused" in error_str.lower():
                self.error_code = "ERR_CONNECTION_REFUSED"
            elif "authentication failed" in error_str.lower():
                self.error_code = "ERR_AUTHENTICATION_FAILED"
            else:
                self.error_code = "ERR_CONNECTION_FAILED"

            self.last_error = f"[{self.error_code}] Failed to initialize connection: {error_str}"
            logger.error(f"Connection initialization failed [{self.error_code}]: {error_str}")
            self.engine = None
            self.db_type = "UNKNOWN"

    def test_connection(self) -> bool:
        if not self.engine:
            return False
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            error_code = "ERR_CONNECTION_TEST"
            error_str = str(e)
            self.last_error = f"[{error_code}] Connection test failed: {error_str}"
            logger.error(f"Connection [{self.db_type}] test failed: {error_str}")
            return False

    def discover_schema(self) -> Dict[str, Any]:
        """
        Introspect the database to get all tables and their columns.
        Does NOT fetch row data — purely structural.
        """
        if not self.engine:
            error_msg = self.last_error or f"[ERR_NO_ENGINE] Database connection not initialized"
            logger.error(f"Schema discovery failed: {error_msg}")
            raise RuntimeError(error_msg)

        try:
            with self.engine.connect() as conn:
                if self.db_type == "ORACLE":
                    # Oracle uses ALL_TABLES and ALL_TAB_COLUMNS
                    tables_result = conn.execute(text(
                        "SELECT table_name FROM all_tables WHERE owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') "
                        "ORDER BY table_name"
                    ))
                else:
                    # PostgreSQL / SQL Server use information_schema
                    tables_result = conn.execute(text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'sys') "
                        "AND table_type = 'BASE TABLE' ORDER BY table_name"
                    ))

                tables = [row[0] for row in tables_result]

                # Get columns for each table
                schema = {"tables": []}
                for table in tables:
                    if self.db_type == "ORACLE":
                        cols_result = conn.execute(text(
                            f"SELECT column_name, data_type FROM all_tab_columns "
                            f"WHERE table_name = :t ORDER BY column_id"
                        ), {"t": table.upper()})
                    else:
                        cols_result = conn.execute(text(
                            "SELECT column_name, data_type FROM information_schema.columns "
                            "WHERE table_name = :t ORDER BY ordinal_position"
                        ), {"t": table})

                    columns = [{"name": row[0], "type": row[1]} for row in cols_result]
                    schema["tables"].append({"name": table, "columns": columns})

                return schema

        except Exception as e:
            error_code = "ERR_SCHEMA_DISCOVERY"
            error_str = str(e)
            self.last_error = f"[{error_code}] Schema discovery error: {error_str}"
            logger.error(f"Connection [{self.db_type}] schema discovery failed: {error_str}")
            raise RuntimeError(self.last_error)

    def extract_data(self, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Execute the configured SQL query and return results."""
        if not self.engine:
            error_msg = self.last_error or f"[ERR_NO_ENGINE] Database connection not initialized"
            logger.error(f"Query execution failed: {error_msg}")
            raise RuntimeError(error_msg)
        try:
            with self.engine.connect() as conn:
                stmt = text(self.query)
                result = conn.execute(stmt, params) if params else conn.execute(stmt)
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            error_code = "ERR_QUERY_EXECUTION"
            error_str = str(e)
            self.last_error = f"[{error_code}] Error executing query: {error_str}"
            logger.error(f"Connection [{self.db_type}] query execution failed: {error_str}")
            raise RuntimeError(self.last_error)

    def extract_table(self, table_name: str, columns: List[str] = None, limit: int = 500) -> List[Dict]:
        """Fetch records from a specific table."""
        if not self.engine:
            error_msg = self.last_error or f"[ERR_NO_ENGINE] Database connection not initialized"
            logger.error(f"Table extraction failed for {table_name}: engine is None, error_code={self.error_code}, last_error={self.last_error}, final_msg={error_msg}")
            raise RuntimeError(error_msg)

        col_clause = ", ".join(columns) if columns else "*"
        query = f"SELECT {col_clause} FROM {table_name} FETCH FIRST {limit} ROWS ONLY" \
            if self.db_type == "ORACLE" \
            else f"SELECT {col_clause} FROM {table_name} LIMIT {limit}"

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                cols = result.keys()
                return [dict(zip(cols, row)) for row in result]
        except Exception as e:
            error_code = "ERR_TABLE_EXTRACTION"
            error_str = str(e)
            self.last_error = f"[{error_code}] Error extracting table {table_name}: {error_str}"
            logger.error(f"Connection [{self.db_type}] table extraction failed for {table_name}: {error_str}")
            raise RuntimeError(self.last_error)

    def close(self):
        if self.engine:
            self.engine.dispose()
