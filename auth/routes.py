import re
import sqlite3
from datetime import datetime

from flask import (
    Blueprint, request, session,
    redirect, url_for, render_template, flash
)
from flask_bcrypt import Bcrypt
from flask import current_app

auth_bp = Blueprint("auth", __name__)
bcrypt  = Bcrypt()


# ── Helpers ───────────────────────────────────────────────────

def get_db():
    return sqlite3.connect(
        current_app.config["DATABASE_PATH"],
        detect_types=sqlite3.PARSE_DECLTYPES
    )

def is_mobile(value: str) -> bool:
    """Return True if value looks like a 10-digit mobile number."""
    return bool(re.fullmatch(r"\d{10}", value.strip()))

def is_email(value: str) -> bool:
    """Return True if value looks like a valid email address."""
    return bool(re.fullmatch(r"[^@]+@[^@]+\.[^@]+", value.strip()))

def login_required(f):
    """Decorator — redirects to login if student is not in session."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "student_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ── Sign Up ───────────────────────────────────────────────────

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if "student_id" in session:
        return redirect(url_for("dashboard.home"))

    if request.method == "GET":
        return render_template("signup.html")

    # ── Collect form data ─────────────────────────────────────
    name       = request.form.get("name", "").strip()
    identifier = request.form.get("identifier", "").strip()   # email OR mobile
    password   = request.form.get("password", "").strip()
    course     = request.form.get("course", "").strip()

    # ── Validation ────────────────────────────────────────────
    errors = []

    if not name:
        errors.append("Full name is required.")

    if not identifier:
        errors.append("Email or mobile number is required.")
    elif not is_email(identifier) and not is_mobile(identifier):
        errors.append("Enter a valid email address or 10-digit mobile number.")

    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")

    if errors:
        for err in errors:
            flash(err, "danger")
        return render_template("signup.html", name=name, identifier=identifier, course=course)

    # ── Determine field type ──────────────────────────────────
    email  = identifier if is_email(identifier)  else None
    mobile = identifier if is_mobile(identifier) else None

    # ── Check for duplicate ───────────────────────────────────
    db = get_db()
    try:
        if email:
            existing = db.execute(
                "SELECT id FROM students WHERE email = ?", (email,)
            ).fetchone()
        else:
            existing = db.execute(
                "SELECT id FROM students WHERE mobile = ?", (mobile,)
            ).fetchone()

        if existing:
            flash("An account with this email / mobile already exists. Please log in.", "warning")
            return render_template("signup.html")

        # ── Hash password & save ──────────────────────────────
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        cursor = db.execute(
            """INSERT INTO students (name, email, mobile, password_hash, course, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, email, mobile, password_hash, course, datetime.utcnow())
        )
        db.commit()
        student_id = cursor.lastrowid

        # ── Auto-login after signup ───────────────────────────
        session.clear()
        session["student_id"]   = student_id
        session["student_name"] = name
        session["course"]       = course
        session.permanent       = True

        flash(f"Welcome, {name}! Your account has been created.", "success")
        return redirect(url_for("dashboard.home"))

    except sqlite3.IntegrityError:
        flash("An account with this email / mobile already exists.", "warning")
        return render_template("signup.html")

    finally:
        db.close()


# ── Login ─────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "student_id" in session:
        return redirect(url_for("dashboard.home"))

    if request.method == "GET":
        return render_template("login.html")

    # ── Collect form data ─────────────────────────────────────
    identifier = request.form.get("identifier", "").strip()
    password   = request.form.get("password", "").strip()

    # ── Basic validation ──────────────────────────────────────
    if not identifier or not password:
        flash("Please enter your email / mobile and password.", "danger")
        return render_template("login.html")

    if not is_email(identifier) and not is_mobile(identifier):
        flash("Enter a valid email address or 10-digit mobile number.", "danger")
        return render_template("login.html")

    # ── Detect field type & query DB ─────────────────────────
    db = get_db()
    try:
        if is_mobile(identifier):
            student = db.execute(
                "SELECT * FROM students WHERE mobile = ? AND is_active = 1",
                (identifier,)
            ).fetchone()
        else:
            student = db.execute(
                "SELECT * FROM students WHERE email = ? AND is_active = 1",
                (identifier,)
            ).fetchone()

        # ── Check student exists & password matches ───────────
        if not student or not bcrypt.check_password_hash(student["password_hash"], password):
            flash("Incorrect email / mobile or password. Please try again.", "danger")
            return render_template("login.html", identifier=identifier)

        # ── Update last_login timestamp ───────────────────────
        db.execute(
            "UPDATE students SET last_login = ? WHERE id = ?",
            (datetime.utcnow(), student["id"])
        )
        db.commit()

        # ── Set session ───────────────────────────────────────
        session.clear()
        session["student_id"]   = student["id"]
        session["student_name"] = student["name"]
        session["course"]       = student["course"]
        session.permanent       = True

        flash(f"Welcome back, {student['name']}!", "success")
        return redirect(url_for("dashboard.home"))

    finally:
        db.close()


# ── Logout ────────────────────────────────────────────────────

@auth_bp.route("/logout")
def logout():
    name = session.get("student_name", "")
    session.clear()
    flash(f"You have been logged out{', ' + name if name else ''}. See you soon!", "info")
    return redirect(url_for("auth.login"))


# ── Profile (view & update) ───────────────────────────────────

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    try:
        student = db.execute(
            "SELECT * FROM students WHERE id = ?",
            (session["student_id"],)
        ).fetchone()

        if request.method == "GET":
            return render_template("profile.html", student=student)

        # ── Update name / course ──────────────────────────────
        new_name   = request.form.get("name", "").strip()
        new_course = request.form.get("course", "").strip()

        if not new_name:
            flash("Name cannot be empty.", "danger")
            return render_template("profile.html", student=student)

        db.execute(
            "UPDATE students SET name = ?, course = ? WHERE id = ?",
            (new_name, new_course, session["student_id"])
        )
        db.commit()

        session["student_name"] = new_name
        session["course"]       = new_course

        flash("Profile updated successfully!", "success")
        return redirect(url_for("auth.profile"))

    finally:
        db.close()


# ── Change Password ───────────────────────────────────────────

@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    current_pw = request.form.get("current_password", "").strip()
    new_pw     = request.form.get("new_password", "").strip()
    confirm_pw = request.form.get("confirm_password", "").strip()

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("auth.profile"))

    if len(new_pw) < 8:
        flash("New password must be at least 8 characters.", "danger")
        return redirect(url_for("auth.profile"))

    db = get_db()
    try:
        student = db.execute(
            "SELECT password_hash FROM students WHERE id = ?",
            (session["student_id"],)
        ).fetchone()

        if not bcrypt.check_password_hash(student["password_hash"], current_pw):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.profile"))

        new_hash = bcrypt.generate_password_hash(new_pw).decode("utf-8")
        db.execute(
            "UPDATE students SET password_hash = ? WHERE id = ?",
            (new_hash, session["student_id"])
        )
        db.commit()

        flash("Password changed successfully!", "success")
        return redirect(url_for("auth.profile"))

    finally:
        db.close()