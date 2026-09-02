# HTTP Route and API Documentation

## Conventions

This is primarily a server-rendered HTML application, not a REST API. Unless noted, successful GETs return HTML `200`; successful mutations usually return `302` redirects with session flash messages. Global errors include `404`, `500`, `413`, `429`, and CSRF rejection (redirect). State-changing forms are CSRF-protected. `A` means authenticated and `Admin` means role `admin`.

## Public and authentication routes

| Method/path | Purpose and input | Auth | Result / notable errors and effects |
| --- | --- | --- | --- |
| `GET /` | Landing page | Public | `200`; logged-in users redirect to dashboard |
| `GET /robots.txt` | Crawl rules and production sitemap URL | Public | `200 text/plain` |
| `GET /sitemap.xml` | Four public production URLs | Public | `200 application/xml` |
| `GET, POST /register` | Form fields: `name`, `email`, `branch`, `cgpa`, optional `skills`, `password`, `confirm_password` | Public | Valid POST inserts student and redirects login; invalid/duplicate returns `200` form with flash; POST limited 5/min |
| `GET /register/google` | Starts Google OIDC registration | Public | Redirects Google, dashboard, or register when unconfigured |
| `GET /register/google/callback` | Consumes provider result | Public | Existing email creates session; new email stores pending name/email; failure redirects register |
| `GET, POST /register/google/complete` | `branch`, `cgpa`, optional `skills`; requires pending session | Pending Google session | Valid POST inserts student with unusable password, signs in, redirects dashboard; validation rerenders; duplicate redirects login |
| `GET, POST /login` | `email`, `password`, optional `remember_me` | Public | Valid POST sets session and redirects dashboard; invalid returns `200`; POST limited 5/min |
| `GET /logout` | Clears session | Public | Redirects login; side effect occurs on GET |
| `GET /login/google` | Starts Google OIDC login | Public | Redirects provider or login when unconfigured |
| `GET /login/google/callback` | Matches provider email to existing student | Public | Sets session and redirects dashboard, otherwise login error |
| `GET, POST /forgot_password` | `email` | Public | Valid-format POST issues OTP only for known user, stores reset session, redirects verify; identical navigation for unknown user; POST limited 3/min |
| `GET, POST /verify_otp` | `otp`; requires reset session | Reset session | Correct live hash deletes OTP and redirects reset; invalid increments attempts and returns form; POST limited 10/min |
| `POST /resend_otp` | No body beyond CSRF; requires reset session | Reset session | Enforces 60s cooldown and 3 session resends, issues replacement OTP, redirects; limited 5/10min |
| `GET, POST /reset_password` | `password`, `confirm_password`; requires recent verification | Verified reset session | Valid POST updates hash, deletes OTPs/flow session, redirects login; expired state redirects forgot-password |

Google callback query parameters and provider error shapes are handled by Authlib and are not explicitly parsed in application code.

## Authenticated HTML routes

| Method/path | Purpose / parameters | Access | Result and side effects |
| --- | --- | --- | --- |
| `GET /dashboard` | Counts, package aggregates, recent rows, role-specific notifications | A | `200` dashboard |
| `GET /companies` | All companies ordered by visit date | A | `200` list |
| `GET /placements` | Joined placement rows ordered by year | A | `200` list; current SQL is not student-scoped |
| `GET, POST /predict` | `cgpa`, comma-separated `skills`, `branch`, integer `backlogs`, `internship=yes/no`, integer `projects` | A | `200`; POST calculates deterministic scores; parsing errors flash and render |
| `GET /profile` | Session user ID | A | `200` profile and own placement rows |
| `GET, POST /change_password` | `current_password`, `new_password`, `confirm_password` | A | Valid POST updates password and redirects profile; errors rerender; POST limited 5/min |

## Admin routes

| Method/path | Purpose / input | Validation, result, side effects |
| --- | --- | --- |
| `GET /students?page=N` | Paginated student list | `page` is typed as int; 20 rows/page; `200` |
| `GET, POST /add_student` | Name, email, branch, CGPA, skills, password | Required text/password pattern/numeric conversion; unique violation rerenders; success inserts and redirects |
| `GET, POST /edit_student/<student_id>` | Editable name/email/branch/CGPA/skills | Missing row or duplicate redirects with flash; success updates |
| `POST /delete_student/<student_id>` | Delete row | Commits delete; caught integrity failure rolls back; redirects students |
| `GET, POST /upload_csv` | Multipart field `csv_file`; UTF-8 `.csv`; headers `name,email,branch,cgpa,skills,password` | Empty/missing/wrong extension rejected; per-row failures skipped; valid passwords hashed; batch commits; max request 16 MB |
| `GET, POST /add_company` | `company_name`, numeric `package`, `required_skills`, `visit_date` | Name and number checked; success inserts |
| `GET, POST /edit_company/<company_id>` | Same fields | Missing row redirects; success updates |
| `POST /delete_company/<company_id>` | Delete row | Commits or catches integrity failure and rolls back |
| `GET, POST /add_placement` | Integer `student_id`, `company_id`, `year`; `status` | FK integrity handled; success commits then makes best-effort Resend notification |
| `POST /delete_placement/<placement_id>` | Delete row | Redirects with success only when `rowcount` is nonzero |
| `GET /analytics` | Aggregate chart data | `200` HTML with five chart datasets |
| `GET /download_report` | Placement report | `200 application/pdf`, attachment `placement_report.pdf` |
| `GET /export_excel` | Placement/student/company workbook | `200` XLSX, attachment `placement_data.xlsx`; string cells are formula-neutralized |

Admin authorization failures redirect dashboard; anonymous access redirects login.

## JSON endpoint

### `GET /api/stats`

- Authentication: any logged-in user.
- Parameters/body: none.
- Side effects: database reads only.
- Success: `200 application/json`.

```json
{
  "total_students": 7,
  "total_placed": 9,
  "placement_rate": 128.6,
  "avg_package": 21.83
}
```

Values above illustrate the response shape using derivable sample concepts; live values depend on data. `total_placed` counts placement rows, so the rate can exceed 100% when a student has multiple placements.

## Error behavior

Unknown routes render `404.html`; unhandled exceptions render `500.html`. Rate limiting flashes and redirects to login. Oversized requests redirect to a same-origin referrer or dashboard. CSRF errors redirect to a same-origin referrer or login. Database connectivity and most uncaught query errors become `500`; no JSON-specific error envelope exists.

