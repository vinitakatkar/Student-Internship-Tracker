CREATE DATABASE IF NOT EXISTS internship_tracker
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE internship_tracker;

CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
  app_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  company_name VARCHAR(100) NOT NULL,
  role_title VARCHAR(100) NOT NULL,
  job_url VARCHAR(500) NULL,
  location VARCHAR(100) NULL,
  application_date DATE NOT NULL,
  status ENUM('Applied','Assessment','Interview','Offer','Rejected') NOT NULL DEFAULT 'Applied',
  deadline_date DATE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_applications_user FOREIGN KEY (user_id)
    REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_app_user_status (user_id, status),
  INDEX idx_app_deadline (user_id, deadline_date)
);
