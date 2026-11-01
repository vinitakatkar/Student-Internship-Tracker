import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "student-tracker-secret-key-2026")
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "internship_tracker.db")


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Applications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            app_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_name TEXT NOT NULL,
            role_title TEXT NOT NULL,
            job_url TEXT,
            location TEXT,
            application_date DATE,
            status TEXT NOT NULL DEFAULT 'Applied',
            deadline_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# Initialize database tables on application start
init_db()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or len(password) < 6:
            flash("Enter your name, email, and a password with at least 6 characters.", "danger")
            return render_template("register.html")

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash("Email already registered. Please log in.", "warning")
                return render_template("register.html")

            cursor.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                (full_name, email, generate_password_hash(password))
            )
            conn.commit()
            flash("Account created! You can now log in.", "success")
            return redirect(url_for("login"))
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, full_name, email, password_hash FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["user_id"]
                session["full_name"] = user["full_name"]
                session["email"] = user["email"]
                flash(f"Welcome back, {user['full_name']}!", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid email or password.", "danger")
        finally:
            conn.close()

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) AS total FROM applications WHERE user_id = ?", (user_id,))
        total_row = cursor.fetchone()
        total = total_row["total"] if total_row else 0

        # Grouped counts by status
        cursor.execute("SELECT status, COUNT(*) AS count FROM applications WHERE user_id = ? GROUP BY status", (user_id,))
        grouped = {row["status"]: row["count"] for row in cursor.fetchall()}

        # All applications
        cursor.execute("""
            SELECT * FROM applications 
            WHERE user_id = ? 
            ORDER BY (deadline_date IS NULL), deadline_date ASC, created_at DESC
        """, (user_id,))
        applications = cursor.fetchall()

        # Deadlines in the next 48 hours
        today_str = date.today().isoformat()
        two_days_str = (date.today() + timedelta(days=2)).isoformat()
        cursor.execute("""
            SELECT * FROM applications 
            WHERE user_id = ? 
            AND deadline_date IS NOT NULL 
            AND deadline_date BETWEEN ? AND ?
            ORDER BY deadline_date ASC
        """, (user_id, today_str, two_days_str))
        urgent = cursor.fetchall()

        return render_template(
            "dashboard.html",
            applications=applications,
            total=total,
            applied=grouped.get("Applied", 0),
            assessment=grouped.get("Assessment", 0),
            interview=grouped.get("Interview", 0),
            offers=grouped.get("Offer", 0),
            rejected=grouped.get("Rejected", 0),
            urgent=urgent,
            today=today_str
        )
    finally:
        conn.close()


# Uses your project's application_form.html template
@app.route("/applications/add", methods=["GET", "POST"])
@login_required
def add_application():
    if request.method == "POST":
        company = request.form.get("company_name", "").strip()
        role = request.form.get("role_title", "").strip()
        job_url = request.form.get("job_url", "").strip() or None
        location = request.form.get("location", "").strip() or None
        applied_on = request.form.get("application_date") or date.today().isoformat()
        status = request.form.get("status", "Applied")
        deadline = request.form.get("deadline_date") or None

        allowed = {"Applied", "Assessment", "Interview", "Offer", "Rejected"}
        if not company or not role or status not in allowed:
            flash("Company, role, and a valid status are required.", "danger")
            return render_template("application_form.html", item=None)

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO applications
                (user_id, company_name, role_title, job_url, location, application_date, status, deadline_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session["user_id"], company, role, job_url, location, applied_on, status, deadline))
            conn.commit()
            flash("Application added successfully!", "success")
            return redirect(url_for("dashboard"))
        finally:
            conn.close()

    # Pass item=None because application_form.html uses it to distinguish Add vs Edit
    return render_template("application_form.html", item=None)


@app.route("/applications/<int:app_id>/edit", methods=["GET", "POST"])
@login_required
def edit_application(app_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE app_id = ? AND user_id = ?", (app_id, session["user_id"]))
        item = cursor.fetchone()

        if not item:
            flash("Application not found.", "danger")
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            company = request.form.get("company_name", "").strip()
            role = request.form.get("role_title", "").strip()
            status = request.form.get("status", "Applied")
            allowed = {"Applied", "Assessment", "Interview", "Offer", "Rejected"}

            if not company or not role or status not in allowed:
                flash("Enter a company, role, and valid status.", "danger")
                return render_template("application_form.html", item=item)

            cursor.execute("""
                UPDATE applications SET 
                    company_name = ?, role_title = ?, job_url = ?,
                    location = ?, application_date = ?, status = ?, deadline_date = ?
                WHERE app_id = ? AND user_id = ?
            """, (
                company,
                role,
                request.form.get("job_url", "").strip() or None,
                request.form.get("location", "").strip() or None,
                request.form.get("application_date") or date.today().isoformat(),
                status,
                request.form.get("deadline_date") or None,
                app_id,
                session["user_id"]
            ))
            conn.commit()
            flash("Application updated successfully.", "success")
            return redirect(url_for("dashboard"))

        return render_template("application_form.html", item=item)
    finally:
        conn.close()


@app.route("/applications/<int:app_id>/delete", methods=["POST"])
@login_required
def delete_application(app_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications WHERE app_id = ? AND user_id = ?", (app_id, session["user_id"]))
        conn.commit()
        flash("Application deleted.", "success")
    finally:
        conn.close()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
