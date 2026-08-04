"""Covers add_student/edit_student duplicate-email handling.

students.email is UNIQUE NOT NULL. The INSERT/UPDATE previously wasn't
wrapped in error handling, so registering or renaming to an already-used
email crashed with an unhandled IntegrityError (500) instead of a
friendly message.
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

import pymysql
from flask_mysqldb import MySQL


def _duplicate_entry_error():
    return pymysql.err.IntegrityError(
        1062, "Duplicate entry 'taken@example.com' for key 'email'"
    )


class StudentEmailUniquenessTests(AppTestCase):
    def test_add_student_with_duplicate_email_shows_friendly_error(self):
        connection, _ = mock_connection(execute_side_effect=_duplicate_entry_error())
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/add_student', data={
                'name': 'New Student',
                'email': 'taken@example.com',
                'branch': 'CSE',
                'cgpa': '8.0',
                'skills': 'Python',
                'password': 'secret123',
            })

        self.assertEqual(response.status_code, 200)  # re-renders the form, no crash
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        # add_student re-renders the template in the same request, so the flash
        # is already consumed into the HTML by the time we see the response --
        # check the body instead of session['_flashes'].
        self.assertIn(b'already registered', response.data)

    def test_add_student_with_new_email_still_succeeds(self):
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
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        self.assertTrue(any('added successfully' in msg for _, msg in self.flashes()))

    def test_edit_student_with_duplicate_email_shows_friendly_error(self):
        connection, _ = mock_connection(execute_side_effect=_duplicate_entry_error())
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/edit_student/5', data={
                'name': 'Existing Student',
                'email': 'taken@example.com',
                'branch': 'CSE',
                'cgpa': '8.0',
                'skills': 'Python',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/edit_student/5', response.headers.get('Location', ''))
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        self.assertTrue(any('already registered' in msg for _, msg in self.flashes()))


if __name__ == '__main__':
    unittest.main()
