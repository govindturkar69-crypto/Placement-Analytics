# AI Agent Guide

## Project overview

Smart Placement Analytics is a server-rendered Flask 3 application for college placement administration and student self-service. The implementation uses an application factory, modular route-registration modules, Jinja templates, a MySQL schema, cookie-backed Flask sessions, and a deterministic placement-readiness scoring rule.

Read `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, and `docs/API.md` before changing behavior.

## Important paths

| Path | Responsibility |
| --- | --- |
| `app.py` | Render/local entry point and compatibility re-exports used by tests |
| `placement_analytics/__init__.py` | Application factory, middleware, extensions, response headers, gzip |
| `placement_analytics/config.py` | Environment-backed Flask/MySQL/session configuration |
| `placement_analytics/extensions.py` | MySQL connection wrapper, CSRF, limiter, OAuth singletons |
| `placement_analytics/routes/` | Route registration grouped by feature |
| `placement_analytics/templates/` | Jinja pages with embedded CSS and JavaScript |
| `database.sql` | Authoritative schema and sample data |
| `tests/` | Mock-based `unittest` route and helper checks |
| `scripts/init_passwords.py` | Legacy one-time helper for hashing existing plaintext database passwords |

## Architecture and coding patterns

- Keep `create_app()` as the composition root. Extension instances remain unbound until `init_app()`.
- Route modules expose `register(app)` and are registered in `placement_analytics/routes/__init__.py`; the project does not use Flask Blueprints.
- Reuse `login_required`, `admin_required`, `auth_version`, `any_blank`, `safe_redirect_back`, `excel_safe`, `send_email`, and the shared extension instances.
- Use parameterized `%s` SQL with tuple arguments. Close cursors and explicitly commit or roll back mutations.
- Preserve the `app.py` re-exports: tests import `app`, `mysql`, `limiter`, and utility functions from that module.
- Follow the existing Python style: small module-level helpers, snake_case, direct route functions, four-space indentation, and single-quoted strings in most Python code.
- Do not add abstractions, frameworks, dependencies, or configuration without a demonstrated need.

## Security and data rules

- State-changing browser actions must use POST and remain CSRF-protected.
- Keep authorization server-side. Protected decorators reload the current account role/password version; `admin_required` protects administration, analytics, imports, and exports. Hiding a UI link is not authorization.
- Never log passwords, OTPs, tokens, API keys, or full reset-email addresses.
- Passwords use Werkzeug hashes. Google-created accounts store an intentionally unusable `google:` value.
- Keep same-origin redirect validation, spreadsheet formula neutralization, upload-size limits, secure cookie settings, security headers, and authentication rate limits.
- Treat `.env` as sensitive and never commit it. Document environment variable names, not values.
- Schema changes require synchronized SQL, query, documentation, and test updates. Preserve foreign-key behavior unless the requested change explicitly changes it.

## API and UI rules

- This is primarily HTML-over-HTTP. `/api/stats` is the only JSON endpoint.
- Preserve route names because templates call them through `url_for()` and tests assert paths.
- Templates extend `base.html` for authenticated screens or `auth_base.html` for authentication screens; landing and error pages are standalone.
- Preserve CSRF tokens in JavaScript-created forms and delete forms.
- Maintain keyboard access, visible labels, responsive breakpoints, and reduced-motion/accessibility behavior already present; do not rely on emoji alone for meaning.
- Chart.js and Google Fonts are CDN-loaded. Avoid adding another frontend dependency for behavior achievable with existing HTML/CSS/JavaScript.

## Dependencies and database

- Dependencies are exact-pinned in `requirements.txt`; do not update them incidentally.
- MySQL access is implemented by the local `MySQL` wrapper in `extensions.py`, not Flask-MySQLdb.
- `students.email` is unique. Placement rows reference students and companies.
- `database.sql` declares cascading foreign keys, while delete routes also handle integrity errors. Verify behavior against the deployed schema before relying on either outcome.
- `scripts/init_passwords.py` uses the same local PyMySQL wrapper as the application.

## Testing and verification

Run the smallest relevant test first, then the full suite when safe:

```powershell
python -m unittest tests.test_predict -v
python -m unittest discover -s tests -v
```

Tests mock MySQL and disable CSRF/rate limiting where needed; they are route/unit checks, not live-database or browser E2E tests. For UI changes, manually verify both roles, narrow/mobile layout, keyboard operation, empty/error states, and CSRF-bearing POST actions.

## Definition of Done

- Requested behavior is implemented with the smallest coherent change.
- Authentication, authorization, validation, failure handling, and data integrity are preserved.
- Relevant tests pass; unrun verification is explicitly reported.
- Documentation is updated when routes, schema, configuration, workflows, or commands change.
- `git diff` contains no secrets, generated artifacts, or unrelated edits.
