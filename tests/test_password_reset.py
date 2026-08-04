"""Covers the DB-backed password reset flow.

Reset tokens used to live in an in-memory dict, which is lost on every
app restart/redeploy and isn't shared across multiple worker processes.
They now live in the password_resets table instead.
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

import app as app_module
from flask_mysqldb import MySQL


class ForgotPasswordTests(AppTestCase):
    def test_existing_email_creates_a_token_and_sends_mail(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1, 'Test User')
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection), \
             patch.object(app_module.mail, 'send') as mock_send:
            response = self.client.post('/forgot_password', data={'email': 'test@example.com'})

        self.assertEqual(response.status_code, 200)
        connection.commit.assert_called_once()
        mock_send.assert_called_once()
        # INSERT into password_resets happened (DELETE cleanup + INSERT = 2 execute calls
        # after the initial SELECT lookup).
        self.assertGreaterEqual(cursor.execute.call_count, 3)
        insert_calls = [c for c in cursor.execute.call_args_list if 'INSERT INTO password_resets' in c.args[0]]
        self.assertEqual(len(insert_calls), 1)

    def test_nonexistent_email_does_not_create_a_token_but_shows_same_message(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection), \
             patch.object(app_module.mail, 'send') as mock_send:
            response = self.client.post('/forgot_password', data={'email': 'nobody@example.com'})

        self.assertEqual(response.status_code, 200)
        connection.commit.assert_not_called()
        mock_send.assert_not_called()
        insert_calls = [c for c in cursor.execute.call_args_list if 'INSERT INTO password_resets' in c.args[0]]
        self.assertEqual(len(insert_calls), 0)
        # Same "If that email exists..." message either way -- no user enumeration.
        self.assertIn(b'reset link has been sent', response.data)


class ResetPasswordTests(AppTestCase):
    def test_invalid_token_redirects_to_login(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/reset_password/does-not-exist')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))
        self.assertTrue(any('Invalid or expired' in msg for _, msg in self.flashes()))

    def test_expired_token_is_deleted_and_redirects_to_forgot_password(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = ('test@example.com', datetime.now() - timedelta(hours=1))
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/reset_password/expired-token')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/forgot_password', response.headers.get('Location', ''))
        connection.commit.assert_called_once()
        delete_calls = [c for c in cursor.execute.call_args_list if 'DELETE FROM password_resets' in c.args[0]]
        self.assertEqual(len(delete_calls), 1)
        self.assertTrue(any('expired' in msg.lower() for _, msg in self.flashes()))

    def test_valid_token_renders_the_form(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = ('test@example.com', datetime.now() + timedelta(hours=1))
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/reset_password/valid-token')

        self.assertEqual(response.status_code, 200)

    def test_too_short_password_is_rejected(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = ('test@example.com', datetime.now() + timedelta(hours=1))
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/reset_password/valid-token', data={'password': 'abc'})

        self.assertEqual(response.status_code, 200)
        connection.commit.assert_not_called()
        update_calls = [c for c in cursor.execute.call_args_list if 'UPDATE students' in c.args[0]]
        self.assertEqual(len(update_calls), 0)

    def test_valid_password_updates_and_consumes_the_token(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = ('test@example.com', datetime.now() + timedelta(hours=1))
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/reset_password/valid-token', data={'password': 'newpass123'})

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))
        connection.commit.assert_called_once()
        update_calls = [c for c in cursor.execute.call_args_list if 'UPDATE students' in c.args[0]]
        delete_calls = [c for c in cursor.execute.call_args_list if 'DELETE FROM password_resets' in c.args[0]]
        self.assertEqual(len(update_calls), 1)
        self.assertEqual(len(delete_calls), 1)
        self.assertTrue(any('successful' in msg.lower() for _, msg in self.flashes()))


if __name__ == '__main__':
    unittest.main()
