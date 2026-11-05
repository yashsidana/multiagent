import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import sqlparse
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from config.settings import settings

logger = logging.getLogger(__name__)

# Disallowed dangerous SQL operations
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "CALL", "LOCK", "RENAME", "SHUTDOWN"
}


class MySQLSafetyException(Exception):
    """Raised when generated SQL violates safety constraints."""
    pass


class MySQLClient:
    """
    Manages MySQL connections and safe read-only query execution for the AI Copilot.
    Enforces AST inspection, SELECT-only rules, and statement limits.
    """

    def __init__(self, readonly: bool = True):
        self.readonly = readonly
        self.connection_uri = (
            settings.mysql_readonly_uri if readonly else settings.mysql_admin_uri
        )
        self.engine: Engine = create_engine(
            self.connection_uri,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True
        )

    def validate_query(self, raw_query: str) -> str:
        """
        Validates that the SQL query is strictly a safe, single SELECT statement.
        Cleans markdown wrappers, checks keywords, and ensures row bounds.
        """
        # 1. Clean query from markdown fences if any
        query = raw_query.strip()
        if query.startswith("```"):
            query = re.sub(r"^```(?:sql)?\s*", "", query, flags=re.IGNORECASE)
            query = re.sub(r"\s*```$", "", query)
        query = query.strip().rstrip(";")

        if not query:
            raise MySQLSafetyException("Query string is empty.")

        # 2. Parse statements with sqlparse
        parsed = sqlparse.parse(query)
        if len(parsed) != 1:
            raise MySQLSafetyException("Multiple statements detected. Only a single SELECT query is permitted.")

        statement = parsed[0]

        # 3. Verify statement starts with SELECT or WITH (for CTEs)
        stmt_type = statement.get_type()
        if stmt_type not in ("SELECT", "UNKNOWN"):
            raise MySQLSafetyException(f"Forbidden statement type: '{stmt_type}'. Only SELECT statements are allowed.")

        # 4. Keyword token inspection
        flat_tokens = [t.value.upper() for t in statement.flatten() if not t.is_whitespace]
        for token in flat_tokens:
            if token in FORBIDDEN_KEYWORDS:
                raise MySQLSafetyException(f"Prohibited SQL keyword detected: '{token}'. Mutation operations are strictly rejected.")

        # 5. Ensure row limit to avoid out-of-memory on large tables
        if not re.search(r"\bLIMIT\s+\d+", query, flags=re.IGNORECASE):
            query = f"{query} LIMIT 50"

        return query

    def execute_query(self, raw_query: str, max_rows: int = 50) -> Dict[str, Any]:
        """
        Validates and executes a SQL query on MySQL read-only connection.
        Returns columns, rows (as dicts), row count, and execution status.
        """
        try:
            validated_query = self.validate_query(raw_query)
            logger.info("Executing validated MySQL query: %s", validated_query)

            with self.engine.connect() as connection:
                # Set a strict statement execution timeout for MySQL (in milliseconds, 5000ms = 5s)
                try:
                    connection.execute(text("SET SESSION max_execution_time=5000;"))
                except Exception:
                    # Older MySQL versions or configurations may skip this setting
                    pass

                result = connection.execute(text(validated_query))
                column_names = list(result.keys()) if result.returns_rows else []
                raw_rows = result.fetchmany(max_rows) if result.returns_rows else []

                # Convert rows to serializable dicts
                rows = [dict(zip(column_names, row)) for row in raw_rows]

                return {
                    "success": True,
                    "query": validated_query,
                    "columns": column_names,
                    "rows": rows,
                    "row_count": len(rows),
                    "error": None
                }

        except MySQLSafetyException as se:
            logger.warning("SQL Safety Violation: %s", str(se))
            return {
                "success": False,
                "query": raw_query,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": f"Security Constraint Violation: {str(se)}"
            }
        except Exception as ex:
            logger.error("MySQL Execution Error: %s", str(ex))
            return {
                "success": False,
                "query": raw_query,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": f"Database Execution Error: {str(ex)}"
            }

    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Tests if the database connection is live."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1;"))
            return True, None
        except Exception as e:
            return False, str(e)


# Pre-instantiated singleton for read-only queries
readonly_mysql_client = MySQLClient(readonly=True)

