"""Focused tests for the SQLite-to-PostgreSQL compatibility layer."""
import unittest

from app.db import _split_sql_statements, _translate_postgres_sql


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

    def test_regular_placeholders_are_translated(self):
        sql, ignored = _translate_postgres_sql("SELECT id FROM demo WHERE tenant_id=? AND status=?")
        self.assertFalse(ignored)
        self.assertEqual(sql, "SELECT id FROM demo WHERE tenant_id=%s AND status=%s")


if __name__ == '__main__':
    unittest.main()
