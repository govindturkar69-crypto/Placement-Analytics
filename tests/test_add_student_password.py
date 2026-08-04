"""Covers the minimum password-length check in add_student.

Previously nothing stopped an admin from leaving the password field
blank -- generate_password_hash('') hashes the empty string, creating
an account whose password is the empty string.
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

from flask_mysqldb import MySQL


class AddStudentPasswordTests(AppTestCase):
    def test_blank_password_is_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/add_student', data={
                'name': 'New Student',
                'email': 'fresh@example.com',
                'branch': 'CSE',
                'cgpa': '8.0',
                'skills': 'Python',
                'password': '',
            })

        self.assertEqual(response.status_code, 200)  # re-renders the form, no insert attempted
        connection.cursor.assert_not_called()
        self.assertIn(b'at least 6 characters', response.data)

    def test_short_password_is_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/add_student', data={
                'name': 'New Student',
                'email': 'fresh@example.com',
                'branch': 'CSE',
                'cgpa': '8.0',
                'skills': 'Python',
                'password': 'abc12',
            })

        self.assertEqual(response.status_code, 200)
        connection.cursor.assert_not_called()
        self.assertIn(b'at least 6 characters', response.data)

    def test_valid_password_still_succeeds(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/add_student', data={
                'name': 'New Student',
                'email': 'fresh@example.com',
                'branch': 'CSE',
                'cgpa': '8.0',
                'skills': 'Python',
                'password': 'secret123',
            })

        self.assertEqual(response.status_code, 302)
        connection.cursor.return_value.execute.assert_called_once()


if __name__ == '__main__':
    unittest.main()
