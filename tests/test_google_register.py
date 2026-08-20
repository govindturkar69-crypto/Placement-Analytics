"""Covers /register/google, /register/google/callback, and
/register/google/complete.

The registration OAuth flow is the fix for the bug where clicking
"Continue with Gmail Account" on the Register page showed
"No account found -- contact your placement cell admin" because it was
hitting the *login* callback which rejects unknown emails.

The new flow:
  1. /register/google          -- kicks off OAuth (separate callback URL)
  2. /register/google/callback -- existing email → log in; new email → pending
  3. /register/google/complete -- collect branch/CGPA/skills → INSERT + log in
"""
import unittest
from unittest.mock import PropertyMock, patch

from flask import redirect
from flask_mysqldb import MySQL

from tests._helpers import mock_connection

import app as app_module
from placement_analytics.extensions import oauth


class GoogleRegisterTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app_module.app.test_client()

    def _configured(self):
        return patch.dict(app_module.app.config, {
            'GOOGLE_CLIENT_ID': 'test-client-id',
            'GOOGLE_CLIENT_SECRET': 'test-client-secret',
        })

    def _unconfigured(self):
        return patch.dict(app_module.app.config, {
            'GOOGLE_CLIENT_ID': None,
            'GOOGLE_CLIENT_SECRET': None,
        })

    # ── /register/google ────────────────────────────────────────────────────

    def test_start_route_declines_when_not_configured(self):
        with self._unconfigured():
            response = self.client.get('/register/google')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/register', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertTrue(any('not set up' in msg for _, msg in sess.get('_flashes', [])))

    def test_start_route_redirects_to_google_when_configured(self):
        with self._configured(), patch.object(
            oauth.google, 'authorize_redirect',
            return_value=redirect('https://accounts.google.com/o/oauth2/auth?fake=1'),
        ) as mock_redirect:
            response = self.client.get('/register/google')

        mock_redirect.assert_called_once()
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response.headers.get('Location', ''))

    def test_already_logged_in_user_is_redirected_to_dashboard(self):
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['role'] = 'student'
            sess['user_id'] = 1
            sess['user_name'] = 'Alice'
        with self._configured():
            response = self.client.get('/register/google')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers.get('Location', ''))

    # ── /register/google/callback ────────────────────────────────────────────

    def test_callback_logs_in_directly_when_email_already_registered(self):
        """If the Google email already has an account, we skip the complete step."""
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (5, 'Bob', 'student')
        with self._configured(), \
             patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection), \
             patch.object(
                 oauth.google, 'authorize_access_token',
                 return_value={'userinfo': {'email': 'bob@gmail.com', 'name': 'Bob'}},
             ):
            response = self.client.get('/register/google/callback')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('logged_in'))
            self.assertEqual(sess.get('user_id'), 5)

    def test_callback_stores_pending_state_for_new_email(self):
        """Unknown email → session stashed → redirect to complete step."""
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None   # no existing account
        with self._configured(), \
             patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection), \
             patch.object(
                 oauth.google, 'authorize_access_token',
                 return_value={'userinfo': {'email': 'newuser@gmail.com', 'name': 'New User'}},
             ):
            response = self.client.get('/register/google/callback')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/register/google/complete', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertNotIn('logged_in', sess)
            self.assertEqual(sess.get('google_pending_email'), 'newuser@gmail.com')
            self.assertEqual(sess.get('google_pending_name'),  'New User')

    def test_callback_declines_when_not_configured(self):
        with self._unconfigured():
            response = self.client.get('/register/google/callback')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/register', response.headers.get('Location', ''))

    def test_callback_handles_oauth_failure_gracefully(self):
        with self._configured(), patch.object(
            oauth.google, 'authorize_access_token', side_effect=Exception('state mismatch'),
        ):
            response = self.client.get('/register/google/callback')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/register', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertNotIn('logged_in', sess)

    # ── /register/google/complete ────────────────────────────────────────────

    def test_complete_get_renders_form_when_pending_state_is_set(self):
        with self.client.session_transaction() as sess:
            sess['google_pending_email'] = 'user@gmail.com'
            sess['google_pending_name']  = 'Test User'

        response = self.client.get('/register/google/complete')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Complete Your Profile', response.data)
        self.assertIn(b'user@gmail.com', response.data)

    def test_complete_get_redirects_to_register_without_pending_state(self):
        response = self.client.get('/register/google/complete')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/register', response.headers.get('Location', ''))

    def test_complete_post_missing_branch_is_rejected(self):
        with self.client.session_transaction() as sess:
            sess['google_pending_email'] = 'user@gmail.com'
            sess['google_pending_name']  = 'Test User'

        response = self.client.post('/register/google/complete', data={
            'branch': '',
            'cgpa':   '7.5',
            'skills': 'Python',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'required', response.data)

    def test_complete_post_invalid_cgpa_is_rejected(self):
        with self.client.session_transaction() as sess:
            sess['google_pending_email'] = 'user@gmail.com'
            sess['google_pending_name']  = 'Test User'

        response = self.client.post('/register/google/complete', data={
            'branch': 'CSE',
            'cgpa':   '15.0',   # out of range
            'skills': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'0.0 and 10.0', response.data)

    def test_complete_post_valid_data_creates_account_and_logs_in(self):
        connection, cursor = mock_connection()
        cursor.lastrowid = 99
        with self.client.session_transaction() as sess:
            sess['google_pending_email'] = 'newstudent@gmail.com'
            sess['google_pending_name']  = 'New Student'

        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/register/google/complete', data={
                'branch': 'CSE',
                'cgpa':   '8.0',
                'skills': 'Python, SQL',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers.get('Location', ''))
        connection.commit.assert_called_once()
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('logged_in'))
            self.assertEqual(sess.get('user_name'), 'New Student')
            self.assertEqual(sess.get('role'), 'student')
            # pending state should be cleaned up
            self.assertNotIn('google_pending_email', sess)
            self.assertNotIn('google_pending_name',  sess)


if __name__ == '__main__':
    unittest.main()
