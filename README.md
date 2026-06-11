# 🎓 Smart Placement Analytics System

A full-stack web application for tracking and analysing college placement data.

## Tech Stack
- **Backend**: Python (Flask)
- **Database**: MySQL
- **Frontend**: HTML + CSS (custom) + Chart.js
- **Analytics**: Pandas

## Features
- 🔐 Student login (session-based auth)
- 👨‍🎓 Student management (add, view)
- 🏢 Company management (add, view)
- ✅ Placement recording
- 📈 Analytics dashboard with 5 charts:
  - Company-wise hiring count (bar)
  - Year-wise placement trend (line)
  - Branch-wise placement % (doughnut)
  - Package distribution (bar)
  - Most in-demand skills (horizontal bar)

## Setup Instructions

### 1. Clone & Install
```bash
git clone <your-repo-url>
cd placement-analytics
pip install -r requirements.txt
```

### 2. Setup MySQL
```bash
mysql -u root -p < database.sql
```

### 3. Configure app.py
Edit these lines in `app.py`:
```python
app.config['MYSQL_PASSWORD'] = 'your_mysql_password'
```

### 4. Run
```bash
python app.py
```
Visit: http://localhost:5000

**Demo login**: govind@example.com / admin123

## Project Structure
```
placement-analytics/
├── app.py              # Flask backend + all routes
├── database.sql        # DB schema + sample data
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html       # Sidebar layout
│   ├── login.html
│   ├── dashboard.html
│   ├── students.html
│   ├── add_student.html
│   ├── companies.html
│   ├── add_company.html
│   ├── placements.html
│   ├── add_placement.html
│   └── analytics.html
└── static/
    └── css/
        └── style.css
```

## API Endpoints
| Route | Method | Description |
|-------|--------|-------------|
| /login | GET/POST | Authentication |
| /dashboard | GET | Overview stats |
| /students | GET | List all students |
| /add_student | POST | Add new student |
| /companies | GET | List all companies |
| /add_company | POST | Add new company |
| /placements | GET | All placements |
| /add_placement | POST | Record placement |
| /analytics | GET | Charts & insights |
| /api/stats | GET | JSON stats summary |
