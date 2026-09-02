"""Covers edit_student/edit_company behavior for a non-existent ID.

GET on a missing ID used to silently render a blank edit form (Jinja
swallows the TypeError on None[1] and renders empty rather than
raising). POST on a missing ID silently updated zero rows while still
flashing a success message. Both now redirect with an honest
"not found" message instead.
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

from placement_analytics.extensions import MySQL


class EditNotFoundTests(AppTestCase):
    def test_get_edit_student_missing_id_redirects_with_flash(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None  # no such student
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/edit_student/99999')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/students', response.headers.get('Location', ''))
        self.assertTrue(any('Student not found' in msg for _, msg in self.flashes()))

    def test_post_edit_student_missing_id_does_not_claim_success(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None  # existence pre-check finds nothing
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/edit_student/99999', data={
                'name': 'Ghost', 'email': 'ghost@example.com', 'branch': 'CSE',
                'cgpa': '8.0', 'skills': 'Python',
            })

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_not_called()
        self.assertTrue(any(
            'not found' in msg and 'success' not in msg.lower()
            for _, msg in self.flashes()
        ))

    def test_get_edit_company_missing_id_redirects_with_flash(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.get('/edit_company/99999')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/companies', response.headers.get('Location', ''))
        self.assertTrue(any('Company not found' in msg for _, msg in self.flashes()))

    def test_post_edit_company_missing_id_does_not_claim_success(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/edit_company/99999', data={
                'company_name': 'Ghost Inc', 'package': '10',
                'required_skills': 'Python', 'visit_date': '2024-01-01',
            })

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_not_called()
        self.assertTrue(any(
            'not found' in msg and 'success' not in msg.lower()
            for _, msg in self.flashes()
        ))

    def test_edit_student_existing_id_still_works(self):
        connection, cursor = mock_connection()
        # First fetchone() is the existence pre-check, must return truthy.
        cursor.fetchone.return_value = (1,)
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/edit_student/1', data={
                'name': 'Real Student', 'email': 'real@example.com', 'branch': 'CSE',
                'cgpa': '8.0', 'skills': 'Python',
            })

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_called_once()
        self.assertTrue(any('updated successfully' in msg for _, msg in self.flashes()))


if __name__ == '__main__':
    unittest.main()
