"""Covers delete_student/delete_company foreign-key handling.

Both routes used to let a FK violation (student/company still referenced
by a placement) bubble up as an unhandled 500. They should now catch it,
roll back, and flash a friendly message instead.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('MYSQL_HOST', 'localhost')
os.environ.setdefault('MYSQL_USER', 'test')
os.environ.setdefault('MYSQL_PASSWORD', 'test')
os.environ.setdefault('MYSQL_DB', 'test')

import pymysql
from flask_mysqldb import MySQL

import app as app_module


def _mock_connection(execute_side_effect=None):
    """A fake MySQL connection whose cursor.execute() can be made to raise."""
    cursor = MagicMock()
    if execute_side_effect is not None:
        cursor.execute.side_effect = execute_side_effect
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


class DeleteRouteTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app_module.app.test_client()
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['role'] = 'admin'
            sess['user_id'] = 1
            sess['user_name'] = 'Admin'

    def _flashes(self):
        with self.client.session_transaction() as sess:
            return sess.get('_flashes', [])

    def test_delete_student_blocked_by_placement_shows_friendly_error(self):
        connection, _ = _mock_connection(
            execute_side_effect=pymysql.err.IntegrityError(
                1451, "Cannot delete or update a parent row: a foreign key constraint fails"
            )
        )
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_student/7')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/students', response.headers.get('Location', ''))
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        self.assertTrue(any('Cannot delete this student' in msg for _, msg in self._flashes()))

    def test_delete_company_blocked_by_placement_shows_friendly_error(self):
        connection, _ = _mock_connection(
            execute_side_effect=pymysql.err.IntegrityError(
                1451, "Cannot delete or update a parent row: a foreign key constraint fails"
            )
        )
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_company/3')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/companies', response.headers.get('Location', ''))
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        self.assertTrue(any('Cannot delete this company' in msg for _, msg in self._flashes()))

    def test_delete_student_without_placements_still_succeeds(self):
        connection, _ = _mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_student/7')

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        self.assertTrue(any('Student deleted successfully' in msg for _, msg in self._flashes()))

    def test_delete_company_without_placements_still_succeeds(self):
        connection, _ = _mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_company/3')

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        self.assertTrue(any('Company deleted successfully' in msg for _, msg in self._flashes()))


if __name__ == '__main__':
    unittest.main()
