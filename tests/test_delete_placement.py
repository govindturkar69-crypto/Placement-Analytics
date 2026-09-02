"""Covers delete_placement's rowcount-based not-found message.

Unlike UPDATE, DELETE's rowcount is unambiguous (a row is either removed
or it isn't -- there's no "matched but unchanged" case), so checking it
directly is safe here in a way it wouldn't be for edit_student/edit_company.
"""
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

from placement_analytics.extensions import MySQL


class DeletePlacementTests(AppTestCase):
    def test_existing_placement_deletes_successfully(self):
        connection, cursor = mock_connection()
        cursor.rowcount = 1
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_placement/1')

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_called_once()
        self.assertTrue(any('deleted successfully' in msg for _, msg in self.flashes()))

    def test_already_deleted_placement_shows_honest_message(self):
        connection, cursor = mock_connection()
        cursor.rowcount = 0
        with patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/delete_placement/999')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(any('already been deleted' in msg for _, msg in self.flashes()))


if __name__ == '__main__':
    unittest.main()
