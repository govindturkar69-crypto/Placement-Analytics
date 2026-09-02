# Technical Requirements Document

## Technical overview

The system is a Python/Flask monolith using server-rendered Jinja templates and direct parameterized SQL against MySQL. `app.py` calls an application factory; feature modules register routes directly on the Flask application. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Technology stack

| Layer | Implementation / reliably determined version |
| --- | --- |
| Runtime | Python 3.11 in GitHub Actions; README requires 3.11+ |
| Web | Flask 3.0.3, Werkzeug 3.0.6, Jinja (via Flask) |
| Database | MySQL protocol through PyMySQL 1.1.1 and a local connection wrapper |
| Auth/security | Werkzeug password hashing, Flask-WTF 1.2.1, Flask-Limiter 3.5.0, Authlib 1.7.2 |
| Documents | ReportLab 4.1.0, OpenPyXL 3.1.2 |
| External HTTP | Requests 2.34.2 |
| Frontend | HTML5, embedded CSS/vanilla JavaScript, Chart.js 4.4.1 CDN, Google Fonts |
| Testing/CI | stdlib `unittest`, `unittest.mock`, GitHub Actions |
| Hosting | Render is identified by entry-point comments, live URL, and proxy handling; deployment manifest is absent |

All direct Python dependencies are exact-pinned in `requirements.txt`. Transitive versions are not determinable without an environment lock/snapshot.

## Configuration

| Variable | Required | Purpose/default |
| --- | --- | --- |
| `MYSQL_HOST` | Yes for database use | MySQL host |
| `MYSQL_USER` | Yes | MySQL user |
| `MYSQL_PASSWORD` | Yes | MySQL password |
| `MYSQL_DB` | Yes | Database name |
| `MYSQL_PORT` | No | Defaults to `3306` |
| `SECRET_KEY` | Yes | Startup fails unless a stable private value is configured |
| `SESSION_COOKIE_SECURE` | No | Defaults to `true`; use `false` for plain-HTTP local development |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Optional pair | Enables Google OIDC login/registration |
| `RESEND_API_KEY` | Optional | Enables email delivery |
| `RESEND_FROM_EMAIL` | Optional | Defaults to Resend onboarding sender |

`.env` is loaded by python-dotenv and ignored by Git. Values must never be documented or committed.

## Runtime and request behavior

- `ProxyFix(x_for=1, x_proto=1, x_host=1)` trusts one reverse-proxy hop.
- MySQL connections are created lazily per Flask application context and closed at teardown; autocommit defaults false.
- Default IP rate limits are 300/day and 60/hour in memory, with stricter authentication limits described in [API.md](API.md).
- Requests above 16 MB receive a handled 413 response.
- Successful 2xx responses of at least 500 bytes are gzipped when accepted.
- Static responses cache for one year; other responses receive no-store/no-cache headers.

## Authentication and authorization

Password login reads a student row by email and verifies its Werkzeug hash. Google OIDC uses discovery metadata and `openid email profile`; login requires a pre-existing email, while registration can create one. Flask’s signed cookie session stores the user identity, role, and an HMAC-backed password version. Protected requests reload the current database role and invalidate deleted accounts or sessions created before a password change.

CSRF protection is global. The application sets HttpOnly, Secure-by-default, SameSite=Lax session cookies and a 30-minute permanent-session lifetime. It emits HSTS on secure requests and additional frame, MIME, XSS, and referrer headers.

## Validation, errors, and logging

Validation is route-specific. Registration has the strongest bounds; admin CRUD validates selected required fields and number conversion, but not every schema/business range. Errors 404, 500, 429, 413, and CSRF failure have custom handling. Most database failures outside specifically caught integrity cases fall through to the 500 handler.

Standard Python logging records masked reset emails, registration events, and email delivery failures. No explicit logging configuration, structured log format, audit log, or monitoring integration exists.

## Build, run, test, and deployment

There is no compile/build step. Typical commands are:

```powershell
python app.py
python -m unittest discover -s tests -v
```

`app.py` listens on `0.0.0.0:5000` with debug disabled when executed directly. GitHub Actions installs requirements on Python 3.11 and runs all unit tests on pushes/pull requests to `main`. A Render start command is referenced but no `render.yaml`, Dockerfile, Procfile, or production WSGI server dependency is present, so the exact production command is unknown / not determinable from repository.

## External services

- Google OIDC endpoints are discovered through Google metadata.
- Resend receives HTTPS email requests with a 10-second timeout; failures return `False` and do not interrupt callers.
- Chart.js and Google Fonts are browser-loaded from public CDNs.

## Constraints and known technical limitations

- Schema setup uses a single SQL file and seed data; there is no migration tool.
- Rate limiting is per process and resets on restart.
- Predictor logic is deterministic, hard-coded, and uncalibrated; it is not machine learning.
- Templates contain substantial inline CSS/JavaScript and CDN dependencies.
- Password-reset email delivery is synchronous, so known and unknown addresses may have observably different response timing.
- The SQL schema declares cascading placement deletes, while route messages anticipate foreign-key restriction; deployed behavior depends on actual production schema.
- No content-security-policy header is configured.
- No live database, OAuth, email, browser, load, or deployment tests are present.
