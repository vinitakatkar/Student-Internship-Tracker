# Student Internship Tracker

A web-based internship application manager based on the uploaded project documentation. It uses Python Flask, MySQL, PyMySQL, Jinja templates, HTML and CSS.

## Features
- Student registration and login; passwords are hashed.
- Add, edit and delete internship applications.
- Track status: Applied, Assessment, Interview, Offer, Rejected.
- Record application date, company, role, job link, location and deadline.
- Dashboard counts and deadlines due within the next 48 hours.
- Each student sees only their own applications.
- SQL queries use parameterized placeholders.

## Requirements
- Python 3.10+
- MySQL 8+
- A browser

## Setup
1. Install and start MySQL.
2. Run `schema.sql` in MySQL Workbench or from a terminal:
   `mysql -u root -p < schema.sql`
3. Open a terminal in this project folder.
4. Create and activate a virtual environment:
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
5. Install packages: `pip install -r requirements.txt`
6. Set the database environment variables from `.env.example`. At minimum set `DB_PASSWORD` and a unique `SECRET_KEY`.
   - Windows PowerShell example:
     `$env:DB_PASSWORD="your_mysql_password"`
     `$env:SECRET_KEY="replace-with-a-long-random-secret"`
   - macOS/Linux example:
     `export DB_PASSWORD='your_mysql_password'`
     `export SECRET_KEY='replace-with-a-long-random-secret'`
7. Start the application: `python app.py`
8. Open `http://127.0.0.1:5000` in your browser and register an account.

## Main pages
- `/register`
- `/login`
- `/dashboard`
- `/applications/add`

## API/documentation note
This starter implementation provides server-rendered Flask routes and MySQL CRUD operations. The PDF also lists JSON REST endpoints (`/api/auth/register`, `/api/auth/login`, `/api/applications`). Those JSON endpoints are not implemented in this starter version; they can be added as a separate API layer if required.

## Security notes
- Change the development secret key before use.
- Do not deploy Flask's debug server in production.
- Use HTTPS and production-grade secret management before hosting publicly.
- This is an academic starter project; test and review it before submitting.
