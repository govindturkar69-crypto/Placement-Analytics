-- ============================================
-- Smart Placement Analytics System - Database
-- ============================================

CREATE DATABASE IF NOT EXISTS placement_db;
USE placement_db;

CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    branch VARCHAR(50) NOT NULL,
    cgpa FLOAT NOT NULL,
    skills TEXT,
    password VARCHAR(200) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companies (
    company_id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    package FLOAT NOT NULL,
    required_skills TEXT,
    visit_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS placements (
    placement_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    company_id INT NOT NULL,
    year INT NOT NULL,
    status VARCHAR(50) DEFAULT 'Selected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

-- One-time passcodes for the forgot-password flow live here instead of an
-- in-memory dict so they survive an app restart/redeploy (Render's free
-- tier sleeps and restarts on inactivity, which would otherwise silently
-- invalidate every outstanding OTP). The code itself is hashed, same as a
-- real password -- a DB leak shouldn't hand out working reset codes.
CREATE TABLE IF NOT EXISTS password_otps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    resend_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_password_otps_email (email)
);

-- Sample company data. User accounts are never seeded; register an account and
-- promote it out-of-band with: UPDATE students SET role='admin' WHERE email='your-admin@example.com';
INSERT INTO companies (company_name, package, required_skills, visit_date) VALUES
('TCS', 7.5, 'Java, Python, SQL', '2024-01-15'),
('Infosys', 6.5, 'Java, Communication', '2024-01-20'),
('Wipro', 7.0, 'Python, Testing', '2024-02-01'),
('Google', 45.0, 'DSA, Python, System Design', '2024-02-10'),
('Amazon', 32.0, 'Java, DSA, Cloud', '2024-02-15'),
('Microsoft', 38.0, 'C++, Java, DSA', '2024-02-20'),
('Accenture', 8.5, 'Any, Communication', '2024-03-01');
