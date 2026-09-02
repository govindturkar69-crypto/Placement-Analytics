"""Covers /login/google and /login/google/callback.

Google sign-in is optional (GOOGLE_CLIENT_ID/SECRET may be unset), so the
routes need to fail gracefully rather than raise when not configured, and
otherwise only ever log a user into an account that already exists --
there's no self-registration flow here.
"""
import unittest
from unittest.mock import PropertyMock, patch

from flask import redirect
from placement_analytics.extensions import MySQL

from tests._helpers import mock_connection

import app as app_module
from placement_analytics.extensions import oauth


class GoogleLoginTests(unittest.TestCase):
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

    def test_start_route_declines_when_not_configured(self):
        with self._unconfigured():
            response = self.client.get('/login/google')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertTrue(any('not set up' in msg for _, msg in sess.get('_flashes', [])))

    def test_callback_declines_when_not_configured(self):
        with self._unconfigured():
            response = self.client.get('/login/google/callback')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))

    def test_start_route_redirects_to_google_when_configured(self):
        with self._configured(), patch.object(
            oauth.google, 'authorize_redirect',
            return_value=redirect('https://accounts.google.com/o/oauth2/auth?fake=1'),
        ) as mock_redirect:
            response = self.client.get('/login/google')

        mock_redirect.assert_called_once()
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response.headers.get('Location', ''))

    def test_callback_logs_in_when_email_matches_an_existing_account(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (7, 'Alice', 'student')
        with self._configured(), \
             patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection), \
             patch.object(
                 oauth.google, 'authorize_access_token',
                 return_value={'userinfo': {'email': 'alice@example.com'}},
             ):
            response = self.client.get('/login/google/callback')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('logged_in'))
            self.assertEqual(sess.get('user_id'), 7)
            self.assertEqual(sess.get('role'), 'student')
            self.assertTrue(sess.permanent)

    def test_callback_denies_an_unmatched_email_without_creating_an_account(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None
        with self._configured(), \
             patch.object(MySQL, 'connection', new_callable=PropertyMock, return_value=connection), \
             patch.object(
                 oauth.google, 'authorize_access_token',
                 return_value={'userinfo': {'email': 'stranger@example.com'}},
             ):
            response = self.client.get('/login/google/callback')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertNotIn('logged_in', sess)
            self.assertTrue(any('No account found' in msg for _, msg in sess.get('_flashes', [])))

    def test_callback_handles_an_oauth_failure_gracefully(self):
        with self._configured(), patch.object(
            oauth.google, 'authorize_access_token', side_effect=Exception('state mismatch'),
        ):
            response = self.client.get('/login/google/callback')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertNotIn('logged_in', sess)
            self.assertTrue(any('Google sign-in failed' in msg for _, msg in sess.get('_flashes', [])))


if __name__ == '__main__':
    unittest.main()
