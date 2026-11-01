import os
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from pymysql.cursors import DictCursor

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY environment variable is missing")


def get_db():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        port=int(os.getenv("DB_PORT", "3306")),
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10,
        charset="utf8mb4"
    )

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

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
        if not full_name or not email or len(password) < 8:
            flash("Enter your name, email, and a password with at least 8 characters.", "danger")
            return render_template("register.html")
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE email=%s", (email,))
                if cur.fetchone():
                    flash("Email already registered. Please log in.", "warning")
                    return render_template("register.html")
                cur.execute(
                    "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
                    (full_name, email, generate_password_hash(password))
                )
            flash("Account created. You can now log in.", "success")
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
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, full_name, password_hash FROM users WHERE email=%s", (email,))
                user = cur.fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["user_id"]
                session["full_name"] = user["full_name"]
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
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM applications WHERE user_id=%s", (session["user_id"],))
            total = cur.fetchone()["total"]
            cur.execute("SELECT status, COUNT(*) AS count FROM applications WHERE user_id=%s GROUP BY status", (session["user_id"],))
            grouped = {row["status"]: row["count"] for row in cur.fetchall()}
            cur.execute("""SELECT * FROM applications WHERE user_id=%s
                           ORDER BY (deadline_date IS NULL), deadline_date ASC, created_at DESC""",
                        (session["user_id"],))
            applications = cur.fetchall()
            cur.execute("""SELECT * FROM applications WHERE user_id=%s AND deadline_date IS NOT NULL
                           AND deadline_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 2 DAY)
                           ORDER BY deadline_date ASC""", (session["user_id"],))
            urgent = cur.fetchall()
        return render_template("dashboard.html", applications=applications, total=total,
                               applied=grouped.get("Applied", 0), assessment=grouped.get("Assessment", 0),
                               interview=grouped.get("Interview", 0), offers=grouped.get("Offer", 0),
                               rejected=grouped.get("Rejected", 0), urgent=urgent)
    finally:
        conn.close()

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
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO applications
                    (user_id, company_name, role_title, job_url, location, application_date, status, deadline_date)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (session["user_id"], company, role, job_url, location, applied_on, status, deadline))
            flash("Application added successfully.", "success")
            return redirect(url_for("dashboard"))
        finally:
            conn.close()
    return render_template("application_form.html", item=None)

@app.route("/applications/<int:app_id>/edit", methods=["GET", "POST"])
@login_required
def edit_application(app_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM applications WHERE app_id=%s AND user_id=%s", (app_id, session["user_id"]))
            item = cur.fetchone()
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
                cur.execute("""UPDATE applications SET company_name=%s, role_title=%s, job_url=%s,
                    location=%s, application_date=%s, status=%s, deadline_date=%s
                    WHERE app_id=%s AND user_id=%s""",
                    (company, role, request.form.get("job_url", "").strip() or None,
                     request.form.get("location", "").strip() or None,
                     request.form.get("application_date") or date.today().isoformat(), status,
                     request.form.get("deadline_date") or None, app_id, session["user_id"]))
                flash("Application updated.", "success")
                return redirect(url_for("dashboard"))
        return render_template("application_form.html", item=item)
    finally:
        conn.close()

@app.route("/applications/<int:app_id>/delete", methods=["POST"])
@login_required
def delete_application(app_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM applications WHERE app_id=%s AND user_id=%s", (app_id, session["user_id"]))
        flash("Application deleted.", "success")
    finally:
        conn.close()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
