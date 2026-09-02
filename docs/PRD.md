# Product Requirements Document

## Product overview

Smart Placement Analytics is a college placement-management web application. Placement-cell administrators maintain students, visiting companies, and placement records; students can register, view shared placement data, inspect their own profile/history, and calculate a rule-based placement-readiness estimate.

The implementation, not marketing language, defines this document. Technical detail is in [TRD.md](TRD.md).

## Problem and goals

The product centralizes placement records that would otherwise be scattered across spreadsheets and manual processes. Its implemented goals are to:

- provide role-aware access for placement staff and students;
- maintain student, company, and placement data;
- summarize outcomes through dashboards and charts;
- support bulk student onboarding and PDF/Excel exports;
- provide password, Google OpenID Connect, and OTP reset flows;
- give students a deterministic readiness estimate and improvement tips.

## Users and roles

| Role | Implemented capabilities |
| --- | --- |
| Public visitor | View landing page, register, sign in, begin password reset, access robots/sitemap resources |
| Student | View dashboard, companies, own placement rows/profile/history, change password, use predictor, call own-scoped stats JSON endpoint |
| Admin | All authenticated views plus student/company/placement management, CSV import, analytics, PDF report, and Excel export |

Authorization is enforced by route decorators. There is no role-management UI.

## Main journeys

1. **Password registration:** visitor supplies name, email, branch, CGPA, optional skills, password, and confirmation; valid unique data creates a student account, then redirects to sign-in.
2. **Google registration:** Google provides name/email; a returning email signs in, while a new email supplies branch, CGPA, and skills before account creation.
3. **Authentication:** a password or matching Google identity establishes a signed session whose account, role, and password version are revalidated on protected requests.
4. **Password recovery:** user submits an email, receives a six-digit OTP when the account exists, verifies it within limits, and sets a new password.
5. **Placement administration:** admin creates students and companies, records a placement, and the system makes a best-effort email notification.
6. **Insight/reporting:** admin views aggregate charts or downloads PDF/Excel representations of current database data.
7. **Student self-service:** student views profile and placement history and submits academic/profile inputs to the readiness calculator.

## Functional requirements reflected by current behavior

| Area | Current requirement / acceptance behavior |
| --- | --- |
| Registration | Required fields, basic email syntax, CGPA 0–10, password of at least eight characters containing a letter and digit, matching confirmation, and unique email are enforced |
| Login | Valid email/password establishes a session; invalid and nonexistent accounts receive the same message; remember-me makes the session permanent |
| Access control | Anonymous users are redirected to login; non-admin users are redirected from admin routes with an error flash |
| Students | Admin can create, edit, delete, list 20 per page, and import CSV rows; duplicate email and selected invalid input produce user-facing errors |
| Companies | Authenticated users can list companies; admin can create, edit, and delete them |
| Placements | Authenticated users can list placements; admin can create/delete rows and trigger a non-blocking notification email |
| Analytics | Admin receives company, year, branch, package, and required-skill aggregates rendered as five charts |
| Predictor | Authenticated user supplies CGPA 0–10, skills, branch, non-negative backlogs, internship status, and non-negative project count; the server returns weighted scores, a chance percentage, company tiers, and tips |
| Reports | Admin can download a placement PDF and a three-sheet XLSX workbook |
| Profile | Authenticated user can view the student row corresponding to the session ID, placement history, and change a password |

## Business rules

- New self-registered and imported users have role `student`; administrators are seeded or database-managed.
- Student email is unique.
- Predictor weights are CGPA 30%, skills 25%, branch 15%, backlogs 15%, internship 10%, and projects 5%.
- Predictor company names are heuristic tiers, not database matches or a trained-model result.
- OTPs expire after 10 minutes, allow five verification attempts, have a 60-second resend cooldown and three session-tracked resends, and grant a 10-minute reset window.
- Forgot-password responses do not disclose whether an email exists.
- Email delivery failure does not roll back a successfully recorded placement or OTP record.

## Inputs and outputs

Inputs include HTML forms, a UTF-8 CSV upload (maximum total request size 16 MB), session cookies, Google OIDC responses, and MySQL records. Outputs include server-rendered HTML, redirects/flash messages, JSON statistics, robots/sitemap text, email requests to Resend, PDF reports, and XLSX workbooks.

## Non-functional behavior

- Security: CSRF, parameterized SQL, password/OTP hashing, secure cookie attributes, rate limits, same-origin redirect checks, spreadsheet formula neutralization, and response security headers.
- Performance: paginated student listing, aggregate SQL, static caching, dynamic-response no-cache headers, and optional gzip for successful responses of at least 500 bytes.
- Responsiveness: templates contain desktop, tablet, and mobile breakpoints.
- Availability: email is best-effort; rate-limit storage is process memory.

## Scope and limitations

Implemented scope is the web application and four-table MySQL schema described above. Not implemented: email verification during ordinary registration, trained machine learning, job applications, interview scheduling, notifications inbox, audit log, role administration, REST CRUD API, live updates, migration framework, live-database integration tests, browser E2E tests, or measured coverage reporting.

Current limitations include hard-coded predictor rules/company tiers, hard-coded production URL in robots/sitemap, in-process rate-limit state, embedded template CSS/JavaScript, no database migration history, and no placement uniqueness constraint. Unknown / not determinable from repository: institutional policy, production database state, production uptime, and actual accessibility conformance.
