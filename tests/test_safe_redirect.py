"""Covers safe_redirect_back(), used by the CSRF and 413 error handlers.

request.referrer is attacker-controlled. In the exact scenario the CSRF
handler fires for (a blocked cross-site forged request), a naive
redirect(request.referrer) would send the victim's browser to whatever
site sent the forged request. safe_redirect_back() must only honor a
same-origin referrer and fall back to a fixed endpoint otherwise.
"""
import unittest

from tests._helpers import AppTestCase

import app as app_module


class SafeRedirectBackTests(AppTestCase):
    def test_same_origin_referrer_is_honored(self):
        with app_module.app.test_request_context(
            '/students', headers={'Referer': 'https://localhost/add_student'}
        ):
            response = app_module.safe_redirect_back('login')
        self.assertIn('/add_student', response.headers['Location'])

    def test_cross_origin_referrer_is_ignored(self):
        with app_module.app.test_request_context(
            '/students', headers={'Referer': 'https://attacker.example/phishing'}
        ):
            response = app_module.safe_redirect_back('login')
        self.assertNotIn('attacker.example', response.headers['Location'])

    def test_missing_referrer_falls_back_to_default(self):
        with app_module.app.test_request_context('/students'):
            response = app_module.safe_redirect_back('login')
        self.assertIn('/login', response.headers['Location'])

    def test_csrf_failure_does_not_redirect_off_site(self):
        # End-to-end: a POST with a bad CSRF token and an attacker Referer
        # must not bounce the browser to that attacker's site.
        app_module.app.config['WTF_CSRF_ENABLED'] = True
        try:
            response = self.client.post(
                '/login',
                data={'email': 'a@b.com', 'password': 'x'},
                headers={'Referer': 'https://attacker.example/evil-form'},
            )
        finally:
            app_module.app.config['WTF_CSRF_ENABLED'] = False

        self.assertEqual(response.status_code, 302)
        self.assertNotIn('attacker.example', response.headers.get('Location', ''))


if __name__ == '__main__':
    unittest.main()
