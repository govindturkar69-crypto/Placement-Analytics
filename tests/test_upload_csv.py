"""Covers upload_csv, including the batch-commit performance fix.

commit() used to run once per row (up to N round-trips for an N-row
upload). It now runs once after the whole batch -- this is safe because
MySQL/InnoDB only rolls back the statement that actually failed, not
rows already inserted earlier in the same transaction.
"""
import io
import unittest
from unittest.mock import PropertyMock, patch

from tests._helpers import AppTestCase, mock_connection

from flask_mysqldb import MySQL


def _csv_file(content):
    return (io.BytesIO(content.encode('utf-8')), 'students.csv')


class UploadCsvTests(AppTestCase):
    def test_all_valid_rows_commits_once(self):
        csv_content = (
            "name,email,branch,cgpa,skills,password\n"
            "Alice,alice@example.com,CSE,8.5,Python,secret123\n"
            "Bob,bob@example.com,IT,7.9,Java,secret123\n"
        )
        connection, cursor = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post(
                '/upload_csv',
                data={'csv_file': _csv_file(csv_content)},
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_called_once()  # not once per row
        insert_calls = [c for c in cursor.execute.call_args_list if 'INSERT INTO students' in c.args[0]]
        self.assertEqual(len(insert_calls), 2)
        self.assertTrue(any('2' in msg and 'added' in msg for _, msg in self.flashes()))

    def test_bad_row_is_skipped_but_good_rows_still_commit(self):
        # cgpa='not-a-number' makes float(row['cgpa']) raise while building the
        # execute() arguments -- before cur.execute() is ever called for that
        # row -- exercising the per-row try/except around the whole insert prep,
        # not just the DB call.
        csv_content = (
            "name,email,branch,cgpa,skills,password\n"
            "Alice,alice@example.com,CSE,8.5,Python,secret123\n"
            "Bad,bad@example.com,CSE,not-a-number,Python,secret123\n"
        )
        connection, cursor = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post(
                '/upload_csv',
                data={'csv_file': _csv_file(csv_content)},
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 302)
        connection.commit.assert_called_once()
        insert_calls = [c for c in cursor.execute.call_args_list if 'INSERT INTO students' in c.args[0]]
        self.assertEqual(len(insert_calls), 1)  # only Alice made it to execute()
        self.assertTrue(any('1' in msg and 'added' in msg for _, msg in self.flashes()))

    def test_missing_required_column_is_rejected_before_touching_db(self):
        csv_content = "name,email,branch\nAlice,alice@example.com,CSE\n"
        connection, cursor = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post(
                '/upload_csv',
                data={'csv_file': _csv_file(csv_content)},
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 302)
        connection.cursor.assert_not_called()
        self.assertTrue(any('Missing columns' in msg for _, msg in self.flashes()))

    def test_non_csv_file_is_rejected(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post(
                '/upload_csv',
                data={'csv_file': (io.BytesIO(b'not a csv'), 'students.txt')},
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 302)
        connection.cursor.assert_not_called()
        self.assertTrue(any('Only CSV files allowed' in msg for _, msg in self.flashes()))


if __name__ == '__main__':
    unittest.main()
