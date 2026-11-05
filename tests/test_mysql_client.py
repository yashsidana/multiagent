import pytest
from src.database.mysql_client import MySQLClient, MySQLSafetyException


@pytest.fixture
def client():
    # Instantiate client without requiring live DB connection for query parsing tests
    return MySQLClient(readonly=True)


def test_valid_select_query(client):
    query = "SELECT customer_id, company_name FROM customers WHERE tier = 'Enterprise'"
    validated = client.validate_query(query)
    assert "SELECT" in validated
    assert "LIMIT 50" in validated


def test_existing_limit_preserved(client):
    query = "SELECT * FROM orders LIMIT 10"
    validated = client.validate_query(query)
    assert validated.endswith("LIMIT 10")
    assert "LIMIT 50" not in validated


def test_markdown_codeblock_stripped(client):
    query = "```sql\nSELECT * FROM products;\n```"
    validated = client.validate_query(query)
    assert validated.startswith("SELECT * FROM products")
    assert "```" not in validated


def test_reject_drop_statement(client):
    with pytest.raises(MySQLSafetyException, match="Forbidden statement type|Prohibited SQL keyword"):
        client.validate_query("DROP TABLE customers;")


def test_reject_delete_statement(client):
    with pytest.raises(MySQLSafetyException, match="Forbidden statement type|Prohibited SQL keyword"):
        client.validate_query("DELETE FROM orders WHERE order_id = 1;")


def test_reject_update_statement(client):
    with pytest.raises(MySQLSafetyException, match="Forbidden statement type|Prohibited SQL keyword"):
        client.validate_query("UPDATE products SET unit_price = 0;")


def test_reject_multiple_statements(client):
    with pytest.raises(MySQLSafetyException, match="Multiple statements detected"):
        client.validate_query("SELECT * FROM customers; DROP TABLE orders;")

