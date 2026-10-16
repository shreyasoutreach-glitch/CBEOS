"""Focused tests for the SQLite-to-PostgreSQL compatibility layer."""
import os
import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.db import _split_sql_statements, _translate_postgres_sql, db


# Every environment variable db() reads when it chooses a backend.
_DB_ENV_KEYS = (
    'CBAM_CUSTOMER_DATA_MODE',
    'CBAM_DB_BACKEND',
    'CBAM_DATABASE_URL',
    'DATABASE_URL',
)


@contextmanager
def database_env(**overrides):
    """Run db() under an explicit configuration, whatever the ambient environment.

    The variables db() reads are removed first, so a value left in a developer
    shell or CI job (for example CBAM_DB_BACKEND=postgres) cannot change which
    branch a test exercises. A variable that is not passed stays unset. The
    original environment is restored on exit.
    """
    env = {k: v for k, v in os.environ.items() if k not in _DB_ENV_KEYS}
    env.update(overrides)
    with patch.dict(os.environ, env, clear=True):
        yield


class PostgresAdapterTests(unittest.TestCase):
    def assert_db_refuses(self, *required_names):
        """db() must raise, name every setting the operator has to fix, and open no connection.

        sqlite3.connect and the PostgreSQL adapter are mocked, so a regression
        that silently falls back to SQLite (or dials a database) fails here
        instead of succeeding quietly. The names are checked independently, so
        the assertions do not depend on how the message orders its clauses.
        """
        with patch('app.db.sqlite3.connect') as sqlite_connect, \\
                patch('app.db._PostgresConnection') as postgres_connection:
            with self.assertRaises(RuntimeError) as raised:
                db()
        message = str(raised.exception)
        for name in required_names:
            self.assertIn(name, message)
        sqlite_connect.assert_not_called()
        postgres_connection.assert_not_called()
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
        # No backend selected and no URL configured: must not fall back to SQLite.
        with database_env(CBAM_CUSTOMER_DATA_MODE='production'):
            self.assert_db_refuses('CBAM_DATABASE_URL', 'CBAM_DB_BACKEND=postgres')

    def test_database_url_does_not_switch_backend_without_explicit_postgres_backend(self):
        with database_env(
            CBAM_CUSTOMER_DATA_MODE='sandbox',
            CBAM_DB_BACKEND='sqlite',
            DATABASE_URL='postgresql://not-used',
        ):
            with patch('app.db.DB_PATH', ':memory:'), \\
                    patch('app.db._PostgresConnection') as postgres_connection:
                connection = db()
                try:
                    self.assertIsInstance(connection, sqlite3.Connection)
                finally:
                    connection.close()
        postgres_connection.assert_not_called()

    def test_production_rejects_sqlite_even_if_database_url_exists(self):
        # A configured URL is not consent to run production on SQLite.
        with database_env(
            CBAM_CUSTOMER_DATA_MODE='production',
            CBAM_DB_BACKEND='sqlite',
            CBAM_DATABASE_URL='postgresql://not-used',
            DATABASE_URL='postgresql://not-used',
        ):
            self.assert_db_refuses('CBAM_DATABASE_URL', 'CBAM_DB_BACKEND=postgres')

    def test_production_does_not_infer_postgres_from_database_url_alone(self):
        # URL present but backend never chosen (the render.yaml shape): still refuse.
        with database_env(
            CBAM_CUSTOMER_DATA_MODE='production',
            CBAM_DATABASE_URL='postgresql://not-used',
        ):
            self.assert_db_refuses('CBAM_DB_BACKEND=postgres')

    def test_explicit_postgres_backend_without_url_refuses_in_every_mode(self):
        for mode in ('sandbox', 'production'):
            with self.subTest(mode=mode):
                with database_env(CBAM_CUSTOMER_DATA_MODE=mode, CBAM_DB_BACKEND='postgres'):
                    self.assert_db_refuses('CBAM_DATABASE_URL')

    def test_explicit_postgres_backend_with_url_selects_postgres_adapter(self):
        # Selection only: the adapter is mocked, so this proves nothing about connectivity.
        with database_env(
            CBAM_CUSTOMER_DATA_MODE='production',
            CBAM_DB_BACKEND='postgres',
            CBAM_DATABASE_URL='postgresql://not-used',
        ):
            with patch('app.db.sqlite3.connect') as sqlite_connect, \\
                    patch('app.db._PostgresConnection') as postgres_connection:
                connection = db()
        postgres_connection.assert_called_once_with('postgresql://not-used')
        self.assertIs(connection, postgres_connection.return_value)
        sqlite_connect.assert_not_called()

    def test_regular_placeholders_are_translated(self):
        sql, ignored = _translate_postgres_sql("SELECT id FROM demo WHERE tenant_id=? AND status=?")
        self.assertFalse(ignored)
        self.assertEqual(sql, "SELECT id FROM demo WHERE tenant_id=%s AND status=%s")


if __name__ == '__main__':
    unittest.main()
