import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

from placement_analytics.extensions import MySQL
from werkzeug.security import generate_password_hash


class RegisterTests(unittest.TestCase):
    def setUp(self):
        import app as app_module
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app_module.app.test_client()

    def test_get_register_renders_form(self):
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create Your Account', response.data)

    def test_logged_in_user_redirects_to_dashboard(self):
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers.get('Location', ''))

    def test_missing_fields_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/register', data={
                'name': 'Test User',
                'email': 'test@example.com',
                # missing branch, cgpa, password, confirm_password
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'All fields except skills are required.', response.data)

    def test_invalid_email_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/register', data={
                'name': 'Test User',
                'email': 'invalid-email',
                'branch': 'CSE',
                'cgpa': '8.5',
                'password': 'Valid1Password!',
                'confirm_password': 'Valid1Password!'
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'valid email address', response.data)

    def test_invalid_cgpa_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/register', data={
                'name': 'Test User',
                'email': 'test@example.com',
                'branch': 'CSE',
                'cgpa': '11.5',
                'password': 'Valid1Password!',
                'confirm_password': 'Valid1Password!'
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CGPA must be a number between 0.0 and 10.0', response.data)

    def test_weak_password_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/register', data={
                'name': 'Test User',
                'email': 'test@example.com',
                'branch': 'CSE',
                'cgpa': '8.5',
                'password': 'weak',
                'confirm_password': 'weak'
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password must be at least 8 characters', response.data)

    def test_mismatched_password_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/register', data={
                'name': 'Test User',
                'email': 'test@example.com',
                'branch': 'CSE',
                'cgpa': '8.5',
                'password': 'Valid1Password!',
                'confirm_password': 'Different1Password!'
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Passwords do not match.', response.data)

    def test_valid_registration_success(self):
        connection, cursor = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/register', data={
                'name': 'Test User',
                'email': 'test@example.com',
                'branch': 'CSE',
                'cgpa': '8.5',
                'skills': 'Python, SQL',
                'password': 'Valid1Password!',
                'confirm_password': 'Valid1Password!'
            })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))
        insert_calls = [c for c in cursor.execute.call_args_list if 'INSERT INTO students' in c.args[0]]
        self.assertEqual(len(insert_calls), 1)

    def test_duplicate_email_rejected(self):
        import pymysql
        def mock_execute(*args, **kwargs):
            if 'INSERT INTO students' in args[0]:
                raise pymysql.err.IntegrityError(1062, "Duplicate entry 'test@example.com' for key 'students.email'")
            
        connection, cursor = mock_connection(execute_side_effect=mock_execute)
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/register', data={
                'name': 'Test User',
                'email': 'test@example.com',
                'branch': 'CSE',
                'cgpa': '8.5',
                'skills': 'Python, SQL',
                'password': 'Valid1Password!',
                'confirm_password': 'Valid1Password!'
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'email is already registered', response.data)

if __name__ == '__main__':
    unittest.main()
