"""Shared setup for app.py route tests. Not a test module itself."""
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('MYSQL_HOST', 'localhost')
os.environ.setdefault('MYSQL_USER', 'test')
os.environ.setdefault('MYSQL_PASSWORD', 'test')
os.environ.setdefault('MYSQL_DB', 'test')

import app as app_module  # noqa: E402


def mock_connection(execute_side_effect=None):
    """A fake MySQL connection whose cursor.execute() can be made to raise."""
    cursor = MagicMock()
    if execute_side_effect is not None:
        cursor.execute.side_effect = execute_side_effect
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


class AppTestCase(unittest.TestCase):
    """Base case with a test client logged in as admin and CSRF disabled."""

    role = 'admin'

    def setUp(self):
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app_module.app.test_client()
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['role'] = self.role
            sess['user_id'] = 1
            sess['user_name'] = 'Admin'

    def flashes(self):
        with self.client.session_transaction() as sess:
            return sess.get('_flashes', [])
