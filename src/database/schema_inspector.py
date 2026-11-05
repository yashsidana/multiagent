import logging
from typing import Dict, List, Any
from sqlalchemy import inspect, text
from src.database.mysql_client import MySQLClient

logger = logging.getLogger(__name__)


class MySQLSchemaInspector:
    """
    Extracts table schemas, column types, foreign keys, and representative sample rows
    from the MySQL database to inject into the Text-to-SQL agent prompt.
    """

    def __init__(self, client: MySQLClient):
        self.client = client
        self._cached_schema: str = ""

    def get_schema_summary(self, force_refresh: bool = False) -> str:
        """
        Builds a clean, human-readable schema description tailored for LLM text-to-SQL.
        Includes table names, column data types, primary/foreign keys, and 2 sample rows.
        """
        if self._cached_schema and not force_refresh:
            return self._cached_schema

        schema_lines: List[str] = []
        inspector = inspect(self.client.engine)

        try:
            table_names = inspector.get_table_names()
        except Exception as e:
            logger.error("Failed to inspect MySQL tables: %s", str(e))
            return "Error retrieving database schema. Ensure MySQL is running."

        for table in table_names:
            schema_lines.append(f"TABLE `{table}` (")
            
            # Columns
            columns = inspector.get_columns(table)
            col_strings = []
            for col in columns:
                col_type = str(col["type"])
                nullability = "NULL" if col.get("nullable", True) else "NOT NULL"
                col_strings.append(f"    `{col['name']}` {col_type} {nullability}")
            
            schema_lines.append(",\n".join(col_strings))
            
            # Foreign keys
            fks = inspector.get_foreign_keys(table)
            if fks:
                schema_lines.append("    -- Relationships:")
                for fk in fks:
                    referred_table = fk["referred_table"]
                    constrained_cols = ", ".join(fk["constrained_columns"])
                    referred_cols = ", ".join(fk["referred_columns"])
                    schema_lines.append(f"    -- FOREIGN KEY ({constrained_cols}) REFERENCES `{referred_table}`({referred_cols})")
            
            schema_lines.append(");")

            # Fetch up to 2 sample rows to give the model real data context
            sample_query = f"SELECT * FROM `{table}` LIMIT 2"
            sample_res = self.client.execute_query(sample_query)
            if sample_res["success"] and sample_res["rows"]:
                schema_lines.append(f"-- Sample rows from `{table}`:")
                for row in sample_res["rows"]:
                    schema_lines.append(f"--   {row}")
            schema_lines.append("")

        self._cached_schema = "\n".join(schema_lines)
        return self._cached_schema


# Singleton inspector instance
schema_inspector = MySQLSchemaInspector(MySQLClient(readonly=True))

