"""Covers the login route itself -- the single most security-critical
path in the app, which had zero direct test coverage before this.
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash


class LoginTests(unittest.TestCase):
    def setUp(self):
        import app as app_module
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app_module.app.test_client()

    def _flashes(self):
        with self.client.session_transaction() as sess:
            return sess.get('_flashes', [])

    def test_correct_credentials_log_in_and_set_session(self):
        stored_hash = generate_password_hash('correct-horse-battery-staple')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1, 'Alice', 'student', stored_hash)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/login', data={
                'email': 'alice@example.com',
                'password': 'correct-horse-battery-staple',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('logged_in'))
            self.assertEqual(sess.get('user_id'), 1)
            self.assertEqual(sess.get('role'), 'student')

    def test_wrong_password_is_rejected(self):
        stored_hash = generate_password_hash('the-real-password')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1, 'Alice', 'student', stored_hash)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/login', data={
                'email': 'alice@example.com',
                'password': 'a-wrong-guess',
            })

        self.assertEqual(response.status_code, 200)  # re-renders login, no redirect
        with self.client.session_transaction() as sess:
            self.assertNotIn('logged_in', sess)
        self.assertIn(b'Invalid email or password', response.data)

    def test_nonexistent_email_gives_the_same_generic_error(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/login', data={
                'email': 'nobody@example.com',
                'password': 'whatever',
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email or password', response.data)

    def test_blank_fields_are_rejected_before_touching_db(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/login', data={'email': '', 'password': ''})

        self.assertEqual(response.status_code, 200)
        connection.cursor.assert_not_called()

    def test_remember_me_checked_makes_the_session_permanent(self):
        stored_hash = generate_password_hash('correct-horse-battery-staple')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1, 'Alice', 'student', stored_hash)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            self.client.post('/login', data={
                'email': 'alice@example.com',
                'password': 'correct-horse-battery-staple',
                'remember_me': 'on',
            })

        with self.client.session_transaction() as sess:
            self.assertTrue(sess.permanent)

    def test_remember_me_unchecked_leaves_the_session_non_permanent(self):
        stored_hash = generate_password_hash('correct-horse-battery-staple')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1, 'Alice', 'student', stored_hash)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            self.client.post('/login', data={
                'email': 'alice@example.com',
                'password': 'correct-horse-battery-staple',
            })

        with self.client.session_transaction() as sess:
            self.assertFalse(sess.permanent)


class AccessControlBoundaryTests(AppTestCase):
    """Confirms @admin_required actually blocks a logged-in student."""

    role = 'student'

    def test_student_cannot_reach_an_admin_only_route(self):
        response = self.client.get('/add_student')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers.get('Location', ''))
        self.assertTrue(any('Access denied' in msg for _, msg in self.flashes()))

    def test_logged_out_user_is_sent_to_login_not_dashboard(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        response = self.client.get('/students')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))


if __name__ == '__main__':
    unittest.main()
