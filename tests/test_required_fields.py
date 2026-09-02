"""Covers the any_blank() required-field guard on add/edit student and company.

None of these forms had any validation that name/email/branch/company_name
weren't blank -- neither a client-side `required` attribute (the forms are
built by JS reading .value directly) nor a server-side check. A blank
submission used to insert a corrupted-looking row with empty strings in
NOT NULL columns (empty string satisfies NOT NULL in MySQL).
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

from placement_analytics.extensions import MySQL


class AnyBlankHelperTests(unittest.TestCase):
    def test_all_non_blank_returns_false(self):
        import app as app_module
        self.assertFalse(app_module.any_blank('Alice', 'a@b.com', 'CSE'))

    def test_any_blank_or_whitespace_only_returns_true(self):
        import app as app_module
        self.assertTrue(app_module.any_blank('Alice', '', 'CSE'))
        self.assertTrue(app_module.any_blank('Alice', '   ', 'CSE'))
        self.assertTrue(app_module.any_blank(None, 'a@b.com', 'CSE'))


class AddStudentRequiredFieldsTests(AppTestCase):
    def test_blank_name_is_rejected_before_touching_db(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/add_student', data={
                'name': '  ', 'email': 'x@example.com', 'branch': 'CSE',
                'cgpa': '8.0', 'skills': 'Python', 'password': 'secret123',
            })

        self.assertEqual(response.status_code, 200)
        connection.cursor.assert_not_called()
        self.assertIn(b'required', response.data)


class EditStudentRequiredFieldsTests(AppTestCase):
    def test_blank_email_is_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/edit_student/1', data={
                'name': 'Alice', 'email': '', 'branch': 'CSE',
                'cgpa': '8.0', 'skills': 'Python',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/edit_student/1', response.headers.get('Location', ''))
        connection.cursor.return_value.execute.assert_not_called()


class AddCompanyRequiredFieldsTests(AppTestCase):
    def test_blank_company_name_is_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/add_company', data={
                'company_name': '', 'package': '10',
                'required_skills': 'Python', 'visit_date': '2024-01-01',
            })

        self.assertEqual(response.status_code, 200)
        connection.cursor.assert_not_called()
        self.assertIn(b'required', response.data)


class EditCompanyRequiredFieldsTests(AppTestCase):
    def test_blank_company_name_is_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/edit_company/1', data={
                'company_name': '   ', 'package': '10',
                'required_skills': 'Python', 'visit_date': '2024-01-01',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/edit_company/1', response.headers.get('Location', ''))
        connection.cursor.return_value.execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
