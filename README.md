<div align="center">

# 🎓 Smart Placement Analytics System

### A full-stack placement management platform with role-based dashboards and ML-powered predictions

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-Visit_App-2563eb?style=for-the-badge)](https://placement-analytics.onrender.com)
[![GitHub](https://img.shields.io/badge/📂_GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/govindturkar69-crypto/Placement-Analytics)

![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3.3-000000?style=flat-square&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Railway-4479A1?style=flat-square&logo=mysql&logoColor=white)
![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=flat-square&logo=render&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-Analytics-FF6384?style=flat-square&logo=chart.js&logoColor=white)

</div>

---

## 📸 Preview

<div align="center">

| Admin Dashboard | Student Portal |
|:---:|:---:|
| ![Admin Dashboard](https://via.placeholder.com/450x280/7f1d1d/ffffff?text=Admin+Dashboard+Screenshot) | ![Student Dashboard](https://via.placeholder.com/450x280/1e293b/ffffff?text=Student+Portal+Screenshot) |

| Analytics Charts | ML Predictor |
|:---:|:---:|
| ![Analytics](https://via.placeholder.com/450x280/2563eb/ffffff?text=Analytics+Charts+Screenshot) | ![ML Predictor](https://via.placeholder.com/450x280/10b981/ffffff?text=ML+Predictor+Screenshot) |

*( Replace these placeholder images — see [📷 Updating Screenshots](#-updating-screenshots) below )*

</div>

---

## ✨ Features

### 👑 Admin Panel
- 🔐 Secure authentication with hashed passwords
- 👨‍🎓 Add & manage student records
- 🏢 Add & manage company records
- ✅ Record placement results
- 📊 Full analytics dashboard access
- 🤖 ML placement predictor

### 🎓 Student Portal
- 🔐 Personal secure login
- 🏢 View companies visiting campus
- ✅ Track personal placement status
- 🤖 Check your own placement chances

### 📈 Analytics Dashboard
| Chart | Insight |
|---|---|
| 📊 Bar Chart | Company-wise hiring count |
| 📈 Line Chart | Year-wise placement trend |
| 🍩 Doughnut Chart | Branch-wise placement % |
| 📊 Bar Chart | Package distribution |
| 📊 Horizontal Bar | Most in-demand skills |

### 🤖 ML Placement Predictor
Enter your **CGPA** + **Skills** → get an instant placement chance percentage with personalized improvement tips.

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|:---|:---|
| **Backend** | Python · Flask |
| **Database** | MySQL (hosted on Railway) |
| **Frontend** | HTML5 · CSS3 · Chart.js |
| **Auth** | Werkzeug password hashing |
| **Deployment** | Render |
| **Version Control** | Git · GitHub |

</div>

---

## 🔐 Demo Credentials

> Try the live app yourself!

| Role | Email | Password |
|---|---|---|
| 👑 **Admin** | `admin@placement.com` | `admin123` |
| 🎓 **Student** | `govind@example.com` | `admin123` |

🔗 **[Launch the App →](https://placement-analytics.onrender.com)**

---

## 📁 Project Structure

```
placement-analytics/
├── app.py                    # Flask backend — all routes & logic
├── database.sql              # Schema + sample seed data
├── requirements.txt          # Python dependencies
├── README.md
├── templates/
│   ├── base.html             # Shared layout (Admin/Student themes)
│   ├── login.html
│   ├── dashboard.html
│   ├── students.html
│   ├── add_student.html
│   ├── companies.html
│   ├── add_company.html
│   ├── placements.html
│   ├── add_placement.html
│   ├── analytics.html        # Chart.js dashboard
│   └── predict.html          # ML predictor UI
└── static/
    └── css/
        └── style.css
```

---

## 🔗 API Routes

| Route | Method | Access | Description |
|---|---|---|---|
| `/login` | GET/POST | Public | Authentication |
| `/dashboard` | GET | Logged in | Overview stats |
| `/students` | GET | Admin | List students |
| `/add_student` | GET/POST | Admin | Add a student |
| `/companies` | GET | All | List companies |
| `/add_company` | GET/POST | Admin | Add a company |
| `/placements` | GET | All | Placement records |
| `/add_placement` | GET/POST | Admin | Record a placement |
| `/analytics` | GET | Admin | Visual analytics |
| `/predict` | GET/POST | All | ML chance predictor |
| `/api/stats` | GET | Logged in | JSON summary stats |
| `/logout` | GET | All | End session |

---

## ⚙️ Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/govindturkar69-crypto/Placement-Analytics.git
cd Placement-Analytics

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up the database
mysql -u root -p < database.sql

# 4. Configure environment variables
# Create a .env file or set these in your shell:
#   MYSQL_HOST=localhost
#   MYSQL_USER=root
#   MYSQL_PASSWORD=your_password
#   MYSQL_DB=placement_db
#   MYSQL_PORT=3306

# 5. Run the app
python app.py
```

Visit **http://localhost:5000** 🎉

---

## 🔒 Security Notes

- Passwords are hashed using **Werkzeug's `generate_password_hash`** — never stored in plain text
- Database credentials are loaded from **environment variables**, never hardcoded in source
- Session-based authentication with role checks (`admin` / `student`) on protected routes

---

## 📷 Updating Screenshots

To replace the placeholder images above with real screenshots:

1. Take a screenshot of each page (Admin dashboard, Student portal, Analytics, Predictor)
2. Save them into a new `screenshots/` folder in the repo, e.g. `screenshots/admin-dashboard.png`
3. Replace each placeholder line in this README:
   ```markdown
   ![Admin Dashboard](https://via.placeholder.com/450x280/...)
   ```
   with:
   ```markdown
   ![Admin Dashboard](screenshots/admin-dashboard.png)
   ```
4. Commit and push — GitHub will render them automatically

---

## 🎯 Interview Summary

> *"I built a full-stack Smart Placement Analytics System using Python Flask and MySQL, featuring role-based authentication with distinct Admin and Student dashboards. Admins manage students, companies, and placement records; students track their own status. I implemented a 5-chart analytics dashboard with Chart.js and a rule-based ML predictor that estimates placement chances from CGPA and skills. Passwords are hashed, credentials are environment-based, and the app is deployed live on Render with a Railway-hosted MySQL database."*

---

## 👨‍💻 Author

**Govind Turkar**
[![GitHub](https://img.shields.io/badge/GitHub-govindturkar69--crypto-181717?style=flat-square&logo=github)](https://github.com/govindturkar69-crypto)

---

<div align="center">

⭐ **If this project helped you, consider giving it a star!** ⭐

</div>
