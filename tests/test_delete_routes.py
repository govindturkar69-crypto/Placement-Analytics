"""Covers delete_student/delete_company foreign-key handling.

Both routes used to let a FK violation (student/company still referenced
by a placement) bubble up as an unhandled 500. They should now catch it,
roll back, and flash a friendly message instead.
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

import pymysql
from placement_analytics.extensions import MySQL


class DeleteRouteTests(AppTestCase):
    def test_delete_student_blocked_by_placement_shows_friendly_error(self):
        connection, _ = mock_connection(
            execute_side_effect=pymysql.err.IntegrityError(
                1451, "Cannot delete or update a parent row: a foreign key constraint fails"
            )
        )
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_student/7')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/students', response.headers.get('Location', ''))
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        self.assertTrue(any('Cannot delete this student' in msg for _, msg in self.flashes()))

    def test_delete_company_blocked_by_placement_shows_friendly_error(self):
        connection, _ = mock_connection(
            execute_side_effect=pymysql.err.IntegrityError(
                1451, "Cannot delete or update a parent row: a foreign key constraint fails"
            )
        )
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_company/3')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/companies', response.headers.get('Location', ''))
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        self.assertTrue(any('Cannot delete this company' in msg for _, msg in self.flashes()))

    def test_delete_student_without_placements_still_succeeds(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_student/7')

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        self.assertTrue(any('Student deleted successfully' in msg for _, msg in self.flashes()))

    def test_delete_company_without_placements_still_succeeds(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_company/3')

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        self.assertTrue(any('Company deleted successfully' in msg for _, msg in self.flashes()))


if __name__ == '__main__':
    unittest.main()
