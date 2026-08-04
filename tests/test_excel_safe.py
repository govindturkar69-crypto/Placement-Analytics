"""Covers excel_safe(), the CSV/Excel formula-injection guard (CWE-1236)
used by export_excel(). A name/skills/company_name value starting with
=, +, -, @, tab, or CR must be neutralized before it reaches a cell,
since Excel treats a leading one of those characters as a formula.
"""
import unittest

from tests._helpers import AppTestCase  # noqa: F401 -- ensures app.py env vars are set

import app as app_module


class ExcelSafeTests(unittest.TestCase):
    def test_formula_prefixes_get_neutralized(self):
        for payload in [
            "=cmd|'/c calc'!A1",
            '+1+1',
            '-2+3',
            '@SUM(A1:A2)',
            '\tsneaky',
            '\rsneaky',
        ]:
            with self.subTest(payload=payload):
                safe = app_module.excel_safe(payload)
                self.assertTrue(safe.startswith("'"))
                self.assertEqual(safe, "'" + payload)

    def test_ordinary_strings_are_untouched(self):
        for value in ['Govind Sharma', 'Python, Java, SQL', 'TCS', '']:
            self.assertEqual(app_module.excel_safe(value), value)

    def test_non_strings_pass_through_unchanged(self):
        for value in [8.5, 12, None]:
            self.assertEqual(app_module.excel_safe(value), value)


if __name__ == '__main__':
    unittest.main()
