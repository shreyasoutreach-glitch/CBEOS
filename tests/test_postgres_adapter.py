"""Focused tests for the SQLite-to-PostgreSQL compatibility layer."""
import os
import unittest
from unittest.mock import patch

from app.db import _split_sql_statements, _translate_postgres_sql, db


class PostgresAdapterTests(unittest.TestCase):
    def test_script_splitter_ignores_semicolons_in_comments_and_strings(self):
        sql = "-- comment; should not split\nCREATE TABLE demo (value TEXT DEFAULT 'a;b');\nCREATE INDEX demo_idx ON demo(value);"
        parts = _split_sql_statements(sql)
        self.assertEqual(len(parts), 2)
        self.assertIn("'a;b'", parts[0])
        self.assertIn('CREATE INDEX demo_idx', parts[1])

    def test_insert_or_ignore_becomes_postgres_conflict_handling(self):
        sql, ignored = _translate_postgres_sql("INSERT OR IGNORE INTO demo(value) VALUES(?)")
        self.assertTrue(ignored)
        self.assertEqual(sql, "INSERT INTO demo(value) VALUES(%s) ON CONFLICT DO NOTHING")

    def test_production_mode_refuses_ephemeral_sqlite_fallback(self):
        env = {
            'CBAM_CUSTOMER_DATA_MODE': 'production',
            'CBAM_DATABASE_URL': '',
            'DATABASE_URL': '',
        }
        with patch.dict(os.environ, env):
            with self.assertRaisesRegex(RuntimeError, 'requires CBAM_DATABASE_URL'):
                db()

    def test_database_url_does_not_switch_backend_without_explicit_postgres_backend(self):
        env = {
            'CBAM_CUSTOMER_DATA_MODE': 'sandbox',
            'CBAM_DB_BACKEND': 'sqlite',
            'CBAM_DATABASE_URL': '',
            'DATABASE_URL': 'postgresql://not-used',
        }
        with patch.dict(os.environ, env):
            with patch('app.db.DB_PATH', ':memory:'):
                connection = db()
                try:
                    self.assertIsInstance(connection, __import__('sqlite3').Connection)
                finally:
                    connection.close()

    def test_production_rejects_sqlite_even_if_database_url_exists(self):
        env = {
            'CBAM_CUSTOMER_DATA_MODE': 'production',
            'CBAM_DB_BACKEND': 'sqlite',
            'CBAM_DATABASE_URL': 'postgresql://not-used',
            'DATABASE_URL': 'postgresql://not-used',
        }
        with patch.dict(os.environ, env):
            with self.assertRaisesRegex(RuntimeError, 'requires CBAM_DB_BACKEND=postgres'):
                db()

    def test_regular_placeholders_are_translated(self):
        sql, ignored = _translate_postgres_sql("SELECT id FROM demo WHERE tenant_id=? AND status=?")
        self.assertFalse(ignored)
        self.assertEqual(sql, "SELECT id FROM demo WHERE tenant_id=%s AND status=%s")


if __name__ == '__main__':
    unittest.main()
