import os
import pymysql
import logging
from pathlib import Path
from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("db_setup")

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "data" / "mysql"


def setup_mysql_database():
    """
    Connects to MySQL as root/admin user and applies schema & read-only permissions scripts.
    """
    logger.info("Connecting to MySQL at %s:%d as root/admin...", settings.MYSQL_HOST, settings.MYSQL_PORT)

    root_password = os.getenv("MYSQL_ROOT_PASSWORD", settings.MYSQL_PASSWORD)

    try:
        conn = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user="root",
            password=root_password,
            charset="utf8mb4",
            autocommit=True
        )
    except Exception as e:
        logger.warning("Could not connect as root: %s. Trying with MYSQL_USER=%s", e, settings.MYSQL_USER)
        try:
            conn = pymysql.connect(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                charset="utf8mb4",
                autocommit=True
            )
        except Exception as e2:
            logger.error("Failed to connect to MySQL: %s", e2)
            print("\n❌ Could not connect to MySQL. Ensure MySQL server is running or start it with 'docker compose up -d mysql'.")
            return

    cursor = conn.cursor()

    # 1. Execute Schema Script
    schema_file = SCRIPTS_DIR / "01_init_schema.sql"
    if schema_file.exists():
        logger.info("Executing %s...", schema_file.name)
        with open(schema_file, "r", encoding="utf-8") as f:
            sql_statements = f.read()

        for stmt in sql_statements.split(";"):
            cleaned = stmt.strip()
            if cleaned:
                try:
                    cursor.execute(cleaned)
                except Exception as e:
                    logger.warning("Statement warning: %s", e)
        logger.info("Successfully loaded schema and seed data.")

    # 2. Execute Read-Only User Setup
    user_file = SCRIPTS_DIR / "02_create_readonly_user.sql"
    if user_file.exists():
        logger.info("Executing %s...", user_file.name)
        with open(user_file, "r", encoding="utf-8") as f:
            user_statements = f.read()

        for stmt in user_statements.split(";"):
            cleaned = stmt.strip()
            if cleaned:
                try:
                    cursor.execute(cleaned)
                except Exception as e:
                    logger.warning("User grant warning: %s", e)
        logger.info("Successfully configured 'copilot_readonly' MySQL role.")

    cursor.close()
    conn.close()
    logger.info("MySQL setup complete!")


if __name__ == "__main__":
    setup_mysql_database()

