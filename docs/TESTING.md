# Testing Documentation

## Strategy and tooling

The repository uses Python’s `unittest` and `unittest.mock`. Tests import the real Flask application, use its test client, disable CSRF, disable the limiter instance, and replace the PyMySQL connection property with `MagicMock` objects. This verifies routing, validation, SQL calls, transaction behavior, sessions, redirects, and rendered messages without a live MySQL service.

Run all tests with:

```powershell
python -m unittest discover -s tests -v
```

GitHub Actions runs the same command on Python 3.11 for pushes and pull requests targeting `main` after installing `requirements.txt`.

## Structure and existing coverage

The suite includes focused route, authentication, validation, data-isolation, and security-boundary tests plus one shared `_helpers.py` module.

| Area | Existing checks |
| --- | --- |
| Login/access | correct/wrong/nonexistent login, remember-me, anonymous redirect, admin denial, role downgrade/account deletion/password-change invalidation, POST logout |
| Registration | render/redirect, required fields, email syntax, CGPA bounds, password strength/match, success, duplicate email |
| Google auth | configured/unconfigured starts/callbacks, existing/new identities, provider failure, completion validation/account creation |
| Password reset | enumeration resistance, OTP issue/hash/expiry/attempts, cooldown/resend limit, verification TTL, password update/session cleanup, combined flow |
| Student/company CRUD | required fields, duplicate email, missing edit records, successful edits/deletes, integrity-error delete behavior |
| Placement | numeric/FK validation, successful insertion, deletion rowcount behavior |
| CSV import | valid batch commit, bad-row skip, required/email/password/CGPA validation, missing headers, non-CSV rejection |
| Predictor | strong/weak profiles, parsing failure, finite/range validation, empty GET state |
| Password change | current password, strength, confirmation, success, form GET |
| Security helpers | same-origin redirect behavior, CSRF redirect safety, spreadsheet formula neutralization, stored-JavaScript boundary, required secret key, gzip `Vary` header |
| Email | missing key, correct Resend request, request failure isolation |

Fixtures are constructed in code; there are no fixture files. External systems are mocked. No coverage artifact or configured percentage threshold exists.

## Test types

- **Unit/route tests:** implemented and dominant.
- **Integration tests:** limited to Flask routing/template/session integration with mocked persistence.
- **Live database integration:** not implemented.
- **End-to-end browser tests:** not implemented.
- **Performance/load/security scanning:** not implemented.

## Important gaps

- Analytics, reports/PDF generation, full Excel workbook response, profile, complete companies/placements rendering, robots/sitemap, most security headers, and custom 404/500 handlers lack direct coverage.
- No real MySQL constraints, transactions, connection teardown, SQL compatibility, or `database.sql` import is exercised.
- No OAuth provider contract, Resend network contract, CDN availability, deployment, or proxy topology is exercised.
- No browser layout, mobile navigation, JavaScript filtering/form submission, Chart.js rendering, keyboard navigation, or accessibility automation exists.
- Boundary validation remains incomplete for some admin-entered package/year/status values.
- The seed password initialization script is not tested.

## Verification procedure

For ordinary changes:

1. Run the most relevant module, e.g. `python -m unittest tests.test_login -v`.
2. Run full discovery.
3. For schema/query changes, additionally use a disposable MySQL database and verify constraints/transactions; this is a manual procedure, not repository automation.
4. For UI changes, manually test public/admin/student flows at desktop and mobile widths with keyboard operation.
5. For integrations, verify configured and unconfigured/failure cases without exposing secrets.

Latest local verification after the documented security/debugging changes: 119 tests passed, Python compilation succeeded, `pip check` reported no broken requirements, and application import plus the public landing route succeeded. Live integrations remain outside this mocked suite.
