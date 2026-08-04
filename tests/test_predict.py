"""Covers the ML predictor's scoring logic -- a non-trivial chunk of
business logic (weighted 6-factor scoring) that had zero test coverage.
This doesn't touch the DB at all, just exercises the /predict route's
computation with a logged-in session.
"""
import unittest

from tests._helpers import AppTestCase


class PredictTests(AppTestCase):
    def test_strong_profile_gets_high_chance(self):
        response = self.client.post('/predict', data={
            'cgpa': '9.5',
            'skills': 'Python, Java, React, DSA, SQL, AWS',
            'branch': 'CSE',
            'backlogs': '0',
            'internship': 'yes',
            'projects': '4',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'High Chance', response.data)

    def test_weak_profile_gets_low_chance(self):
        response = self.client.post('/predict', data={
            'cgpa': '5.5',
            'skills': '',
            'branch': 'Civil',
            'backlogs': '5',
            'internship': 'no',
            'projects': '0',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Very Low Chance', response.data)

    def test_invalid_cgpa_shows_friendly_error_not_a_crash(self):
        response = self.client.post('/predict', data={
            'cgpa': 'not-a-number',
            'skills': 'Python',
            'branch': 'CSE',
            'backlogs': '0',
            'internship': 'no',
            'projects': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error', response.data)

    def test_get_request_renders_empty_state(self):
        response = self.client.get('/predict')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'result will appear here', response.data)


if __name__ == '__main__':
    unittest.main()
