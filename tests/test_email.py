"""Covers placement_analytics/email.py -- the Resend-based mail sender
that replaced Flask-Mail/SMTP after confirming Render blocks raw
outbound SMTP (OSError: [Errno 101] Network is unreachable).
"""
import unittest
from unittest.mock import patch, MagicMock

from placement_analytics.email import send_email


class SendEmailTests(unittest.TestCase):
    def test_returns_false_and_does_not_call_requests_when_api_key_missing(self):
        with patch.dict('os.environ', {}, clear=True), \
             patch('placement_analytics.email.requests.post') as mock_post:
            result = send_email('student@example.com', 'Subject', 'Body')

        self.assertFalse(result)
        mock_post.assert_not_called()

    def test_sends_via_resend_api_with_the_right_payload(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        with patch.dict('os.environ', {'RESEND_API_KEY': 'test-key'}), \
             patch('placement_analytics.email.requests.post', return_value=mock_response) as mock_post:
            result = send_email('student@example.com', 'Your Code', 'body text')

        self.assertTrue(result)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-key')
        self.assertEqual(kwargs['json']['to'], ['student@example.com'])
        self.assertEqual(kwargs['json']['subject'], 'Your Code')
        self.assertEqual(kwargs['json']['text'], 'body text')

    def test_network_failure_returns_false_instead_of_raising(self):
        import requests
        with patch.dict('os.environ', {'RESEND_API_KEY': 'test-key'}), \
             patch('placement_analytics.email.requests.post', side_effect=requests.RequestException('boom')):
            result = send_email('student@example.com', 'Subject', 'Body')

        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
