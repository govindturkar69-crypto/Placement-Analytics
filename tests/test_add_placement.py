"""Covers add_placement error handling.

The INSERT previously had no error handling at all: a non-existent
student_id/company_id threw an unhandled FK IntegrityError (500), and
a non-numeric year threw an unhandled DataError (500) under MySQL
strict mode. Same bug class as delete_student/delete_company and
add_student/edit_student.
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

import pymysql
from placement_analytics.extensions import MySQL


class AddPlacementTests(AppTestCase):
    def test_nonexistent_student_or_company_shows_friendly_error(self):
        connection, _ = mock_connection(
            execute_side_effect=pymysql.err.IntegrityError(
                1452, "Cannot add or update a child row: a foreign key constraint fails"
            )
        )
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/add_placement', data={
                'student_id': '999',
                'company_id': '1',
                'year': '2024',
                'status': 'Selected',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/add_placement', response.headers.get('Location', ''))
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        self.assertTrue(any('no longer exists' in msg for _, msg in self.flashes()))

    def test_non_numeric_year_is_rejected_before_touching_db(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/add_placement', data={
                'student_id': '1',
                'company_id': '1',
                'year': 'not-a-year',
                'status': 'Selected',
            })

        self.assertEqual(response.status_code, 302)
        connection.cursor.return_value.execute.assert_not_called()
        self.assertTrue(any('valid student, company, and year' in msg for _, msg in self.flashes()))

    def test_valid_placement_still_succeeds(self):
        connection, cursor = mock_connection()
        cursor.fetchone.side_effect = [('Govind', 'govind@example.com'), ('TCS', 7.5)]
        # Without this mock a passing test would attempt a real HTTPS call to
        # Resend for the placement-confirmation email.
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection), \
             patch('placement_analytics.routes.placements.send_email') as mock_send:
            response = self.client.post('/add_placement', data={
                'student_id': '1',
                'company_id': '1',
                'year': '2024',
                'status': 'Selected',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/placements', response.headers.get('Location', ''))
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        self.assertTrue(any('recorded successfully' in msg for _, msg in self.flashes()))


if __name__ == '__main__':
    unittest.main()
