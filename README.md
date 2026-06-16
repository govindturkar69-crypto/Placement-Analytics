# 🎓 Smart Placement Analytics System

A full-stack web application for managing and analyzing college placement data with role-based access control and ML-based placement prediction.

🌐 **Live Demo:** [https://placement-analytics.onrender.com](https://placement-analytics.onrender.com)

📂 **GitHub:** [github.com/govindturkar69-crypto/Placement-Analytics](https://github.com/govindturkar69-crypto/Placement-Analytics)

---

## 🚀 Features

### 👑 Admin Panel (Dark Red Theme)
- Secure login with admin credentials
- Add, view and manage students
- Add and manage companies
- Record placement results
- View interactive analytics dashboard with 5 charts
- ML-based placement prediction

### 🎓 Student Portal (Dark Blue Theme)
- Secure login with student credentials
- View companies visiting for placements
- Check personal placement status
- ML-based placement chance prediction

### 📊 Analytics Dashboard
- Company-wise hiring count (Bar Chart)
- Year-wise placement trend (Line Chart)
- Branch-wise placement % (Doughnut Chart)
- Package distribution (Bar Chart)
- Most in-demand skills (Horizontal Bar Chart)

### 🤖 ML Placement Predictor
- Enter CGPA + Skills
- Get instant placement chance percentage
- Personalized tips to improve chances

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python Flask |
| Database | MySQL (Railway) |
| Frontend | HTML, CSS, Chart.js |
| Deployment | Render |
| Database Host | Railway.app |

---

## 🔐 Demo Login Credentials

### Admin Login:
```
URL:      https://placement-analytics.onrender.com
Email:    admin@placement.com
Password: admin123
```

### Student Login:
```
URL:      https://placement-analytics.onrender.com
Email:    govind@example.com
Password: admin123
```

---

## 📁 Project Structure

```
placement-analytics/
├── app.py                    # Flask backend + all routes
├── database.sql              # DB schema + sample data
├── requirements.txt          # Python dependencies
├── README.md
├── templates/
│   ├── base.html             # Sidebar layout (Admin/Student theme)
│   ├── login.html            # Login page
│   ├── dashboard.html        # Main dashboard
│   ├── students.html         # Students list
│   ├── add_student.html      # Add student form
│   ├── companies.html        # Companies list
│   ├── add_company.html      # Add company form
│   ├── placements.html       # Placements list
│   ├── add_placement.html    # Record placement form
│   ├── analytics.html        # Charts & insights
│   └── predict.html          # ML Predictor page
└── static/
    └── css/
        └── style.css         # Custom styles
```

---

## 🔗 API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/login` | GET/POST | Authentication |
| `/dashboard` | GET | Overview stats |
| `/students` | GET | List all students |
| `/add_student` | GET/POST | Add new student |
| `/companies` | GET | List all companies |
| `/add_company` | GET/POST | Add new company |
| `/placements` | GET | All placements |
| `/add_placement` | GET/POST | Record placement |
| `/analytics` | GET | Charts & insights |
| `/predict` | GET/POST | ML prediction |
| `/api/stats` | GET | JSON stats |
| `/logout` | GET | Logout |

---

## ⚙️ Local Setup

### Step 1 — Clone repo
```bash
git clone https://github.com/govindturkar69-crypto/Placement-Analytics.git
cd Placement-Analytics
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Setup MySQL
```bash
mysql -u root -p < database.sql
```

### Step 4 — Update app.py
```python
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PASSWORD'] = 'your_password'
```

### Step 5 — Run
```bash
python app.py
```
Visit: http://localhost:5000

---

## 🎯 Interview Answer

> "I developed a full-stack Smart Placement Analytics System using Python Flask and MySQL. The system features role-based authentication with separate Admin and Student portals. Admins can manage students, companies, and placement records, while students can view their placement status. I implemented an interactive analytics dashboard using Chart.js with 5 different chart types, and a rule-based ML placement predictor that calculates placement chances based on CGPA and skills. The project is deployed live on Render with Railway MySQL as the cloud database."

---

## 📦 Requirements

```
flask==2.3.3
flask-mysqldb==1.0.1
PyMySQL==1.1.0
cryptography==41.0.7
Werkzeug==2.3.7
```

---

## 👨‍💻 Developer

**Govind Turkar**
- GitHub: [@govindturkar69-crypto](https://github.com/govindturkar69-crypto)

---

⭐ **Star this repo if you found it helpful!**
