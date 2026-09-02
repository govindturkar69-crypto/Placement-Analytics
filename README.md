<div align="center">

<img src="screenshots/logo.png" alt="Placement Analytics Logo" width="100" height="100">

# Smart Placement Analytics Platform

**A full-stack college placement management system with role-based dashboards, analytics, and a weighted placement-readiness predictor.**

[![Live Demo](https://img.shields.io/badge/Live_Demo-placement--analytics.onrender.com-2563eb?style=for-the-badge)](https://placement-analytics.onrender.com)
[![Source](https://img.shields.io/badge/Source-GitHub-181717?style=for-the-badge&logo=github)](https://github.com/govindturkar69-crypto/Placement-Analytics)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?style=flat-square&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/Database-MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white)
![Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=flat-square&logo=render&logoColor=white)
[![Tests](https://github.com/govindturkar69-crypto/Placement-Analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/govindturkar69-crypto/Placement-Analytics/actions/workflows/tests.yml)

</div>

---

## 🎯 Overview

The **Smart Placement Analytics Platform** modernizes how colleges manage their placement drives. It provides two distinct experiences: one for the **Placement Cell (Admins)** to track data, generate reports, and manage companies, and another for **Students** to register, monitor their status, and estimate placement readiness using a transparent deterministic scoring rule.

---

## ✨ Key Features

<details open>
<summary><b>👨‍🎓 Student Experience</b></summary>

- **Self-Registration:** Password-based onboarding or optional Google OAuth.
- **Personalized Dashboard:** Track your placement status, view visiting companies, and monitor trends.
- **Placement Predictor:** Estimate readiness with a deterministic weighted scoring rule.
- **Profile Management:** Highlight skills, CGPA, projects, and internships to calculate a readiness score.
- **Secure Access:** OTP-based password resets sent directly via email.
</details>

<details open>
<summary><b>👑 Admin Capabilities (Placement Cell)</b></summary>

- **Comprehensive Data Management:** Add, edit, or remove students and companies easily.
- **Bulk Import:** Seamlessly upload hundreds of student records via CSV.
- **Real-Time Analytics:** Visualize placement data across 5 distinct chart types (Branch-wise, Year-over-Year, Skill demand, etc.).
- **Automated Communication:** Instant email notifications sent to students upon successful placement.
- **Export & Reporting:** Generate polished PDF reports or multi-sheet Excel exports in a single click.
</details>

---

## 🧠 Placement Readiness Predictor

The application uses a transparent six-factor heuristic to produce a readiness estimate. It is not a trained machine-learning model and should not be treated as a calibrated probability:

| Factor | Weight | Impact Area |
| :--- | :---: | :--- |
| **CGPA** | `30%` | Baseline academic performance and consistency. |
| **Skills** | `25%` | Skill count matched against current industry demand. |
| **Branch** | `15%` | Historical placement rates for the specific department. |
| **Backlogs** | `15%` | Impact of active or past academic backlogs. |
| **Internship** | `10%` | Prior industry experience and practical exposure. |
| **Projects** | `5%` | Depth and relevance of project portfolio. |

*Output includes an overall probability score, a factor-by-factor breakdown, tier matches for companies, and actionable improvement tips.*

---

## 📊 Analytics Dashboard

Admins have access to a rich, interactive data visualization suite:

- **Bar Charts:** Company-wise hiring count and package distribution.
- **Line Charts:** Year-over-year placement growth trends.
- **Doughnut Charts:** Branch-wise placement share and distribution.
- **Horizontal Bars:** Most in-demand technical and soft skills.

---

## 🛡️ Enterprise-Grade Security

Security is deeply integrated into the platform's architecture:

- **Authentication:** Passwords use Werkzeug's adaptive password hashing; protected requests revalidate the current database role and password version.
- **Protection Against Attacks:**
  - **CSRF:** Flask-WTF tokens secure every state-changing form.
  - **SQLi:** Parameterized queries used globally.
  - **XSS:** Jinja autoescaping and safe JSON serialization.
- **Session Security:** `HttpOnly`, `Secure`, and `SameSite=Lax` cookies with a 30-minute permanent-session lifetime; password changes, account deletion, and role downgrades invalidate stale authorization.
- **Rate Limiting:** IP-based throttling on authentication and password reset routes.
- **Transport Security:** Enforced HSTS and strict security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).

---

## 🛠️ Technology Stack

| Component | Technologies Used |
| :--- | :--- |
| **Backend Framework** | Python 3.11+, Flask 3.0.3 |
| **Database** | MySQL |
| **Frontend** | HTML5, CSS3 (Vanilla CSS with Custom Properties), Chart.js |
| **Security & Auth** | Werkzeug, Flask-WTF, Flask-Limiter, Google OAuth |
| **Document Generation**| ReportLab (PDF), OpenPyXL (Excel) |
| **Email Service** | Resend API (HTTPS-based delivery) |
| **Testing & CI/CD** | `unittest`, GitHub Actions |
| **Cloud Hosting** | Render |

---

## 🚀 Local Setup & Installation

Get the platform running locally in minutes.

### Prerequisites
- Python 3.11 or higher
- MySQL Server

### 1. Clone & Install
```bash
git clone https://github.com/govindturkar69-crypto/Placement-Analytics.git
cd Placement-Analytics
pip install -r requirements.txt
```

### 2. Database Setup
```bash
mysql -u root -p < database.sql
```
Register the initial user, then promote it to administrator directly in MySQL:
```sql
UPDATE students SET role='admin' WHERE email='your-admin@example.com';
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=placement_db
MYSQL_PORT=3306
SECRET_KEY=your_super_secret_key
```
`SECRET_KEY` is mandatory. Startup fails when it is missing so deployments cannot silently use an unstable signing key.

### 4. Run the Application
```bash
python app.py
```
Access the application at `http://localhost:5000`.

### Running Tests
The test suite utilizes a mocked database layer, meaning it can run without an active MySQL connection.
```bash
python -m unittest discover -s tests -v
```

---

## 🔌 Optional Integrations

### "Continue with Google" Setup
To enable Google OAuth for quick registration and login:
1. Create an **OAuth 2.0 Client ID** (Web application) in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Add both local callbacks to your Authorized redirect URIs:
   - `http://localhost:5000/login/google/callback`
   - `http://localhost:5000/register/google/callback`
3. Update your `.env`:
   ```env
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

### Email Delivery (Resend API)
For OTPs and placement notifications, the platform uses [Resend](https://resend.com) to bypass typical SMTP blocks on cloud providers.
1. Obtain an API key from Resend.
2. Update your `.env`:
   ```env
   RESEND_API_KEY=your_api_key
   RESEND_FROM_EMAIL=Placement Analytics <onboarding@resend.dev>
   ```

---

## 📂 Project Architecture

Detailed implementation documentation is available in [`docs/`](docs/), including product, technical, architecture, database, route/API, UI/UX, and testing references.

```text
placement-analytics/
├── app.py                      # Application entry point
├── database.sql                # Schema & sample company data
├── .env                        # Local ignored environment configuration (never commit)
├── placement_analytics/        # Core application package
│   ├── __init__.py             # App factory & initialization
│   ├── routes/                 # Blueprint-style modular routes
│   ├── templates/              # Jinja2 HTML templates
│   └── static/                 # CSS, JS, and Images
├── scripts/                    # Utility scripts (e.g., password hashing)
├── tests/                      # Unit testing suite
└── .github/workflows/          # CI/CD pipelines
```

---

## 👨‍💻 Developer

<div align="center">

**Govind Turkar**

[![GitHub](https://img.shields.io/badge/GitHub-govindturkar69--crypto-181717?style=for-the-badge&logo=github)](https://github.com/govindturkar69-crypto)

</div>
