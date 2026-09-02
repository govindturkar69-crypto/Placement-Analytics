import unittest
from unittest.mock import PropertyMock, patch

from placement_analytics.extensions import MySQL
from tests._helpers import AppTestCase, mock_connection


class StudentDataScopeTests(AppTestCase):
    role = 'student'

    def test_placements_query_is_scoped_to_logged_in_student(self):
        connection, cursor = mock_connection()
        cursor.fetchall.return_value = []

        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/placements')

        self.assertEqual(response.status_code, 200)
        query, params = cursor.execute.call_args.args
        self.assertIn('WHERE p.student_id=%s', query)
        self.assertEqual(params, (1,))

    def test_dashboard_queries_are_scoped_to_logged_in_student(self):
        connection, cursor = mock_connection()
        cursor.fetchone.side_effect = [
            (1, 7, 1, 12.0, 12.0),
            ('Own Company', 12.0, 'Selected'),
        ]
        cursor.fetchall.return_value = [('Student', 'Own Company', 12.0, 2026, 'Selected')]

        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/dashboard')

        self.assertEqual(response.status_code, 200)
        calls = cursor.execute.call_args_list
        self.assertEqual(calls[0].args[1], (1, 1, 1))
        self.assertIn('WHERE p.student_id=%s', calls[1].args[0])
        self.assertEqual(calls[1].args[1], (1,))
        self.assertEqual(calls[2].args[1], (1,))

    def test_stats_api_query_is_scoped_to_logged_in_student(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1, 1, 12.0)

        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/api/stats')

        self.assertEqual(response.status_code, 200)
        query, params = cursor.execute.call_args.args
        self.assertIn('WHERE student_id=%s', query)
        self.assertIn('WHERE pl.student_id=%s', query)
        self.assertEqual(params, (1, 1))


if __name__ == '__main__':
    unittest.main()
