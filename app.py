import os
import sqlite3
from datetime import date
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
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")


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


# Initialize database tables on startup
init_db()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        hashed_pw = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                (full_name, email, hashed_pw),
            )
            conn.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["email"] = user["email"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM applications WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    applications = cursor.fetchall()

    # Calculate status counts
    counts = {"Applied": 0, "OA": 0, "Interview": 0, "Offer": 0, "Rejected": 0}
    for app_item in applications:
        status = app_item["status"]
        if status in counts:
            counts[status] += 1

    conn.close()
    return render_template(
        "dashboard.html",
        applications=applications,
        counts=counts,
        total_count=len(applications),
        today=date.today().isoformat(),
    )


@app.route("/applications/add", methods=["GET", "POST"])
@login_required
def add_application():
    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        role_title = request.form.get("role_title", "").strip()
        job_url = request.form.get("job_url", "").strip()
        location = request.form.get("location", "").strip()
        application_date = request.form.get("application_date") or date.today().isoformat()
        status = request.form.get("status", "Applied")
        deadline_date = request.form.get("deadline_date") or None

        if not company_name or not role_title:
            flash("Company name and Role title are required.", "danger")
            return render_template("add_application.html")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO applications 
            (user_id, company_name, role_title, job_url, location, application_date, status, deadline_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                company_name,
                role_title,
                job_url,
                location,
                application_date,
                status,
                deadline_date,
            ),
        )
        conn.commit()
        conn.close()

        flash("Application logged successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_application.html")


@app.route("/applications/update-status/<int:app_id>", methods=["POST"])
@login_required
def update_status(app_id):
    new_status = request.form.get("status")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE applications SET status = ? WHERE app_id = ? AND user_id = ?",
        (new_status, app_id, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Status updated.", "info")
    return redirect(url_for("dashboard"))


@app.route("/applications/delete/<int:app_id>", methods=["POST"])
@login_required
def delete_application(app_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM applications WHERE app_id = ? AND user_id = ?",
        (app_id, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Application removed.", "info")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
