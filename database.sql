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

-- Sample Data
INSERT INTO students (name, email, branch, cgpa, skills, password) VALUES
('Govind Sharma', 'govind@example.com', 'CSE', 8.5, 'Python, Java, MySQL', 'admin123'),
('Priya Patel', 'priya@example.com', 'CSE', 9.1, 'React, Node.js, Python', 'admin123'),
('Rahul Verma', 'rahul@example.com', 'IT', 7.8, 'Java, Spring Boot, SQL', 'admin123'),
('Sneha Gupta', 'sneha@example.com', 'ECE', 8.2, 'C++, Python, ML', 'admin123'),
('Amit Kumar', 'amit@example.com', 'CSE', 7.5, 'Java, HTML, CSS', 'admin123'),
('Pooja Singh', 'pooja@example.com', 'IT', 8.9, 'Python, Django, PostgreSQL', 'admin123');

INSERT INTO companies (company_name, package, required_skills, visit_date) VALUES
('TCS', 7.5, 'Java, Python, SQL', '2024-01-15'),
('Infosys', 6.5, 'Java, Communication', '2024-01-20'),
('Wipro', 7.0, 'Python, Testing', '2024-02-01'),
('Google', 45.0, 'DSA, Python, System Design', '2024-02-10'),
('Amazon', 32.0, 'Java, DSA, Cloud', '2024-02-15'),
('Microsoft', 38.0, 'C++, Java, DSA', '2024-02-20'),
('Accenture', 8.5, 'Any, Communication', '2024-03-01');

INSERT INTO placements (student_id, company_id, year, status) VALUES
(1, 4, 2024, 'Selected'),
(2, 5, 2024, 'Selected'),
(3, 1, 2024, 'Selected'),
(4, 3, 2024, 'Selected'),
(5, 2, 2024, 'Selected'),
(6, 7, 2024, 'Selected'),
(1, 6, 2023, 'Selected'),
(2, 4, 2023, 'Selected'),
(3, 2, 2023, 'Selected');
