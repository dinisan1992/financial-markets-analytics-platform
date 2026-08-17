from __future__ import annotations

try:
    from mysql.connector.connection import MySQLConnection
    from mysql.connector.cursor import MySQLCursor
except ImportError:  # pragma: no cover - mysqlconnector is a runtime dependency
    MySQLConnection = ()
    MySQLCursor = None

try:
    from mysql.connector.connection_cext import CMySQLConnection
    from mysql.connector.cursor_cext import CMySQLCursor
except ImportError:  # pragma: no cover - depends on connector build
    CMySQLConnection = ()
    CMySQLCursor = None


def unbuffered_mysql_cursor(driver_connection):
    """Create a genuinely unbuffered mysqlconnector cursor or fail closed."""
    if CMySQLCursor is not None and isinstance(driver_connection, CMySQLConnection):
        cursor = driver_connection.cursor(cursor_class=CMySQLCursor)
    elif MySQLCursor is not None and isinstance(driver_connection, MySQLConnection):
        cursor = driver_connection.cursor(cursor_class=MySQLCursor)
    else:
        cursor = driver_connection.cursor(buffered=False)

    if getattr(cursor, "_buffered", False) or "Buffered" in type(cursor).__name__:
        cursor.close()
        raise RuntimeError(
            "mysqlconnector returned a buffered cursor for a bounded scan"
        )
    return cursor
