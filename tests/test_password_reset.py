"""Covers the OTP-based password reset flow: request a code, verify it,
then set a new password. Session-gated rather than link-in-URL, so most
of these tests drive multiple requests through the same test client and
inspect the session between them.
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import PropertyMock, patch

from tests._helpers import mock_connection

import app as app_module
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash


class OtpFlowTestCase(unittest.TestCase):
    def setUp(self):
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app_module.app.test_client()

    def _flashes(self):
        with self.client.session_transaction() as sess:
            return sess.get('_flashes', [])

    def _set_reset_session(self, email='test@example.com', last_sent=None, resend_count=0, verified_at=None):
        with self.client.session_transaction() as sess:
            sess['reset_email'] = email
            if last_sent is not None:
                sess['otp_last_sent_at'] = last_sent.isoformat()
            if verified_at is not None:
                sess['otp_verified_at'] = verified_at.isoformat()
            sess['otp_resend_count'] = resend_count


class ForgotPasswordTests(OtpFlowTestCase):
    def test_invalid_email_format_is_rejected_before_touching_db(self):
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/forgot_password', data={'email': 'not-an-email'})

        self.assertEqual(response.status_code, 200)
        connection.cursor.assert_not_called()
        self.assertIn(b'valid email', response.data)

    def test_matched_email_issues_an_otp_and_redirects_to_verify(self):
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1, 'Test User')
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection), \
             patch('placement_analytics.routes.auth.send_email') as mock_send:
            response = self.client.post('/forgot_password', data={'email': 'test@example.com'})

        self.assertEqual(response.status_code, 302)
        self.assertIn('/verify_otp', response.headers.get('Location', ''))
        mock_send.assert_called_once()
        insert_calls = [c for c in cursor.execute.call_args_list if 'INSERT INTO password_otps' in c.args[0]]
        self.assertEqual(len(insert_calls), 1)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('reset_email'), 'test@example.com')

    def test_unmatched_email_still_redirects_to_verify_with_no_otp_issued(self):
        """Same response either way -- this must not be usable to probe
        which emails have accounts."""
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection), \
             patch('placement_analytics.routes.auth.send_email') as mock_send:
            response = self.client.post('/forgot_password', data={'email': 'nobody@example.com'})

        self.assertEqual(response.status_code, 302)
        self.assertIn('/verify_otp', response.headers.get('Location', ''))
        mock_send.assert_not_called()
        insert_calls = [c for c in cursor.execute.call_args_list if 'INSERT INTO password_otps' in c.args[0]]
        self.assertEqual(len(insert_calls), 0)


class VerifyOtpTests(OtpFlowTestCase):
    def test_get_without_session_redirects_to_forgot_password(self):
        response = self.client.get('/verify_otp')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/forgot_password', response.headers.get('Location', ''))

    def test_no_otp_row_shows_a_generic_invalid_message(self):
        self._set_reset_session()
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = None
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/verify_otp', data={'otp': '123456'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'incorrect or has expired', response.data)

    def test_correct_code_marks_verified_and_redirects_to_reset_password(self):
        self._set_reset_session()
        otp_hash = generate_password_hash('123456')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (99, otp_hash, datetime.now() + timedelta(minutes=5), 0)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/verify_otp', data={'otp': '123456'})

        self.assertEqual(response.status_code, 302)
        self.assertIn('/reset_password', response.headers.get('Location', ''))
        delete_calls = [c for c in cursor.execute.call_args_list if 'DELETE FROM password_otps WHERE id' in c.args[0]]
        self.assertEqual(len(delete_calls), 1)  # one-time use
        with self.client.session_transaction() as sess:
            self.assertIn('otp_verified_at', sess)

    def test_wrong_code_increments_attempts_and_shows_generic_message(self):
        self._set_reset_session()
        otp_hash = generate_password_hash('123456')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (99, otp_hash, datetime.now() + timedelta(minutes=5), 0)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/verify_otp', data={'otp': '000000'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'incorrect or has expired', response.data)
        update_calls = [c for c in cursor.execute.call_args_list if 'attempts=attempts+1' in c.args[0]]
        self.assertEqual(len(update_calls), 1)

    def test_expired_code_is_rejected(self):
        self._set_reset_session()
        otp_hash = generate_password_hash('123456')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (99, otp_hash, datetime.now() - timedelta(minutes=1), 0)
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/verify_otp', data={'otp': '123456'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'incorrect or has expired', response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn('otp_verified_at', sess)

    def test_max_attempts_exceeded_locks_out_even_the_correct_code(self):
        self._set_reset_session()
        otp_hash = generate_password_hash('123456')
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (99, otp_hash, datetime.now() + timedelta(minutes=5), 5)  # already at the cap
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/verify_otp', data={'otp': '123456'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'incorrect or has expired', response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn('otp_verified_at', sess)


class ResendOtpTests(OtpFlowTestCase):
    def test_without_session_redirects_to_forgot_password(self):
        response = self.client.post('/resend_otp')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/forgot_password', response.headers.get('Location', ''))

    def test_within_cooldown_is_rejected_without_touching_the_db(self):
        self._set_reset_session(last_sent=datetime.now())
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/resend_otp')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/verify_otp', response.headers.get('Location', ''))
        connection.cursor.assert_not_called()
        self.assertTrue(any('wait a moment' in msg for _, msg in self._flashes()))

    def test_after_cooldown_issues_a_new_otp(self):
        self._set_reset_session(last_sent=datetime.now() - timedelta(minutes=5), resend_count=0)
        connection, cursor = mock_connection()
        cursor.fetchone.return_value = (1, 'Test User')
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection), \
             patch('placement_analytics.routes.auth.send_email') as mock_send:
            response = self.client.post('/resend_otp')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/verify_otp', response.headers.get('Location', ''))
        mock_send.assert_called_once()
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('otp_resend_count'), 1)

    def test_resend_limit_reached_sends_the_user_back_to_forgot_password(self):
        self._set_reset_session(last_sent=datetime.now() - timedelta(minutes=5), resend_count=3)
        connection, _ = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/resend_otp')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/forgot_password', response.headers.get('Location', ''))
        connection.cursor.assert_not_called()
        with self.client.session_transaction() as sess:
            self.assertNotIn('reset_email', sess)


class ResetPasswordTests(OtpFlowTestCase):
    def test_without_verified_session_redirects_to_forgot_password(self):
        response = self.client.get('/reset_password')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/forgot_password', response.headers.get('Location', ''))

    def test_stale_verification_redirects_to_forgot_password(self):
        self._set_reset_session(verified_at=datetime.now() - timedelta(minutes=15))
        response = self.client.get('/reset_password')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/forgot_password', response.headers.get('Location', ''))

    def test_get_with_valid_session_renders_the_form(self):
        self._set_reset_session(verified_at=datetime.now())
        response = self.client.get('/reset_password')

        self.assertEqual(response.status_code, 200)

    def test_weak_password_is_rejected(self):
        self._set_reset_session(verified_at=datetime.now())
        connection, cursor = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/reset_password', data={
                'password': 'alllowercase', 'confirm_password': 'alllowercase',
            })

        self.assertEqual(response.status_code, 200)
        update_calls = [c for c in cursor.execute.call_args_list if 'UPDATE students' in c.args[0]]
        self.assertEqual(len(update_calls), 0)

    def test_mismatched_confirmation_is_rejected(self):
        self._set_reset_session(verified_at=datetime.now())
        connection, cursor = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/reset_password', data={
                'password': 'newpass123', 'confirm_password': 'somethingelse456',
            })

        self.assertEqual(response.status_code, 200)
        update_calls = [c for c in cursor.execute.call_args_list if 'UPDATE students' in c.args[0]]
        self.assertEqual(len(update_calls), 0)

    def test_valid_password_updates_clears_otps_and_the_session(self):
        self._set_reset_session(verified_at=datetime.now())
        connection, cursor = mock_connection()
        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection):
            response = self.client.post('/reset_password', data={
                'password': 'newpass123', 'confirm_password': 'newpass123',
            })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))
        update_calls = [c for c in cursor.execute.call_args_list if 'UPDATE students' in c.args[0]]
        delete_calls = [c for c in cursor.execute.call_args_list if 'DELETE FROM password_otps WHERE email' in c.args[0]]
        self.assertEqual(len(update_calls), 1)
        self.assertEqual(len(delete_calls), 1)
        with self.client.session_transaction() as sess:
            self.assertNotIn('reset_email', sess)
            self.assertNotIn('otp_verified_at', sess)
        self.assertTrue(any('successful' in msg.lower() for _, msg in self._flashes()))


class FullOtpJourneyTests(OtpFlowTestCase):
    def test_request_verify_and_reset_end_to_end(self):
        connection, cursor = mock_connection()
        fixed_otp = '123456'
        otp_hash = generate_password_hash(fixed_otp)

        with patch.object(MySQL, 'connect', new_callable=PropertyMock, return_value=connection), \
             patch('placement_analytics.routes.auth.send_email'), \
             patch('placement_analytics.routes.auth._generate_otp', return_value=fixed_otp):
            cursor.fetchone.return_value = (1, 'Test User')
            step1 = self.client.post('/forgot_password', data={'email': 'test@example.com'})
            self.assertIn('/verify_otp', step1.headers.get('Location', ''))

            cursor.fetchone.return_value = (99, otp_hash, datetime.now() + timedelta(minutes=5), 0)
            step2 = self.client.post('/verify_otp', data={'otp': fixed_otp})
            self.assertIn('/reset_password', step2.headers.get('Location', ''))

            step3 = self.client.post('/reset_password', data={
                'password': 'brandnewpass1', 'confirm_password': 'brandnewpass1',
            })
            self.assertIn('/login', step3.headers.get('Location', ''))


if __name__ == '__main__':
    unittest.main()
