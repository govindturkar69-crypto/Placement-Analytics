import unittest
from unittest.mock import PropertyMock, patch

from placement_analytics.config import Config
from placement_analytics.decorators import auth_version
from placement_analytics.extensions import MySQL
from tests._helpers import AppTestCase, app_module, mock_connection


class SessionAuthorizationTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app_module.app.test_client()

    def _set_admin_session(self, password_hash='stored-hash'):
        with app_module.app.test_request_context():
            version = auth_version(password_hash)
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 7
            sess['user_name'] = 'Former Admin'
            sess['role'] = 'admin'
            sess['auth_version'] = version

    def test_database_role_downgrade_revokes_admin_access(self):
        self._set_admin_session()
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = ('Former Admin', 'student', 'stored-hash')

        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/students')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers['Location'])

    def test_deleted_account_clears_session(self):
        self._set_admin_session()
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None

        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/students')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])
        with self.client.session_transaction() as sess:
            self.assertNotIn('logged_in', sess)

    def test_changed_password_invalidates_existing_session(self):
        self._set_admin_session('old-hash')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = ('Admin', 'admin', 'new-hash')

        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/students')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_missing_secret_key_fails_fast(self):
        from placement_analytics import create_app

        with patch.object(Config, 'SECRET_KEY', None):
            with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
                create_app()


class BrowserBoundaryTests(AppTestCase):
    def test_logout_requires_post(self):
        self.assertEqual(self.client.get('/logout').status_code, 405)
        response = self.client.post('/logout')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_student_name_is_not_interpolated_into_javascript(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1,)
        cursor.fetchall.return_value = [
            (1, "');alert(1);//", 'student@example.com', 'CSE', 8.0, 'Python'),
        ]

        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/students')

        html = response.get_data(as_text=True)
        self.assertNotIn("confirmDelete('');alert(1);//", html)
        self.assertIn('confirmDelete(this.dataset.confirmName)', html)

    def test_invalid_student_page_is_clamped_to_first_page(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []

        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/students?page=-4')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(cursor.execute.call_args.args[1], (20, 0))

    def test_responses_vary_on_accept_encoding(self):
        response = self.client.get('/predict', headers={'Accept-Encoding': 'gzip'})
        self.assertIn('Accept-Encoding', response.headers.get('Vary', ''))


if __name__ == '__main__':
    unittest.main()
