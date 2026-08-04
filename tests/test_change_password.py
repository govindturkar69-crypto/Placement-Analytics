"""Covers the self-service /change_password route.

Previously the only ways to change a password were the email-based
Forgot Password flow (logged out) or a direct DB update -- there was no
way for a logged-in user to change their own password. This route
requires the current password before accepting a new one.
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash


class ChangePasswordTests(AppTestCase):
    def test_wrong_current_password_is_rejected(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (generate_password_hash('the-real-password'),)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/change_password', data={
                'current_password': 'a-wrong-guess',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123',
            })

        self.assertEqual(response.status_code, 200)  # re-renders the form, no crash
        connection.commit.assert_not_called()
        self.assertIn(b'Current password is incorrect', response.data)

    def test_too_short_new_password_is_rejected(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (generate_password_hash('correct-current-password'),)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/change_password', data={
                'current_password': 'correct-current-password',
                'new_password': 'abc',
                'confirm_password': 'abc',
            })

        self.assertEqual(response.status_code, 200)
        connection.commit.assert_not_called()
        self.assertIn(b'at least 6 characters', response.data)

    def test_mismatched_confirmation_is_rejected(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (generate_password_hash('correct-current-password'),)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/change_password', data={
                'current_password': 'correct-current-password',
                'new_password': 'newpassword123',
                'confirm_password': 'somethingelse456',
            })

        self.assertEqual(response.status_code, 200)
        connection.commit.assert_not_called()
        self.assertIn(b'do not match', response.data)

    def test_valid_change_succeeds(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (generate_password_hash('correct-current-password'),)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/change_password', data={
                'current_password': 'correct-current-password',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/profile', response.headers.get('Location', ''))
        connection.commit.assert_called_once()
        update_calls = [c for c in cursor.execute.call_args_list if 'UPDATE students' in c.args[0]]
        self.assertEqual(len(update_calls), 1)
        self.assertTrue(any('changed successfully' in msg for _, msg in self.flashes()))

    def test_get_request_renders_the_form(self):
        response = self.client.get('/change_password')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
