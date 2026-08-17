from unittest.mock import Mock, patch
import unittest

from services.mysql_streaming_service import unbuffered_mysql_cursor


class MysqlStreamingServiceTests(unittest.TestCase):
    def test_cext_connection_forces_unbuffered_cursor_class(self):
        class FakeConnection:
            def __init__(self):
                self.cursor_calls = []

            def cursor(self, **kwargs):
                self.cursor_calls.append(kwargs)
                return Mock(_buffered=False)

        class ForcedCursor:
            pass

        connection = FakeConnection()
        with patch(
            "services.mysql_streaming_service.CMySQLConnection",
            FakeConnection,
        ), patch(
            "services.mysql_streaming_service.CMySQLCursor",
            ForcedCursor,
        ):
            cursor = unbuffered_mysql_cursor(connection)

        self.assertIsNotNone(cursor)
        self.assertEqual(
            [{"cursor_class": ForcedCursor}],
            connection.cursor_calls,
        )

    def test_buffered_cursor_is_closed_and_rejected(self):
        cursor = Mock(_buffered=True)
        connection = Mock()
        connection.cursor.return_value = cursor

        with self.assertRaisesRegex(RuntimeError, "buffered cursor"):
            unbuffered_mysql_cursor(connection)

        cursor.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
