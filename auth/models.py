import sqlite3
from datetime import datetime
from flask import current_app


# ── DB Connection Helper ──────────────────────────────────────

def get_db():
    db = sqlite3.connect(
        current_app.config["DATABASE_PATH"],
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    db.row_factory = sqlite3.Row
    return db


# ── Student Model ─────────────────────────────────────────────

class Student:
    """
    Represents a student account in the students table.

    Table schema:
        id            INTEGER  PRIMARY KEY AUTOINCREMENT
        name          TEXT     NOT NULL
        email         TEXT     UNIQUE
        mobile        TEXT     UNIQUE
        password_hash TEXT     NOT NULL
        course        TEXT
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        last_login    DATETIME
        is_active     BOOLEAN  DEFAULT 1
    """

    TABLE = "students"

    def __init__(self, row):
        """Build a Student object from a sqlite3.Row."""
        self.id            = row["id"]
        self.name          = row["name"]
        self.email         = row["email"]
        self.mobile        = row["mobile"]
        self.password_hash = row["password_hash"]
        self.course        = row["course"]
        self.created_at    = row["created_at"]
        self.last_login    = row["last_login"]
        self.is_active     = bool(row["is_active"])

    def to_dict(self):
        """Return a safe dictionary — password_hash excluded."""
        return {
            "id"         : self.id,
            "name"       : self.name,
            "email"      : self.email,
            "mobile"     : self.mobile,
            "course"     : self.course,
            "created_at" : str(self.created_at),
            "last_login" : str(self.last_login),
            "is_active"  : self.is_active,
        }

    def __repr__(self):
        return f"<Student id={self.id} name={self.name!r}>"


    # ── CREATE ────────────────────────────────────────────────

    @staticmethod
    def create(name, password_hash, course, email=None, mobile=None):
        """
        Insert a new student into the database.
        Returns the new Student object, or None on duplicate.
        """
        db = get_db()
        try:
            cursor = db.execute(
                """INSERT INTO students
                       (name, email, mobile, password_hash, course, created_at, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (name, email, mobile, password_hash, course, datetime.utcnow())
            )
            db.commit()
            return Student.get_by_id(cursor.lastrowid)

        except sqlite3.IntegrityError:
            # Duplicate email or mobile
            return None

        finally:
            db.close()


    # ── READ ──────────────────────────────────────────────────

    @staticmethod
    def get_by_id(student_id):
        """Fetch a single Student by primary key. Returns None if not found."""
        db = get_db()
        try:
            row = db.execute(
                "SELECT * FROM students WHERE id = ?",
                (student_id,)
            ).fetchone()
            return Student(row) if row else None
        finally:
            db.close()

    @staticmethod
    def get_by_email(email):
        """Fetch an active Student by email. Returns None if not found."""
        db = get_db()
        try:
            row = db.execute(
                "SELECT * FROM students WHERE email = ? AND is_active = 1",
                (email,)
            ).fetchone()
            return Student(row) if row else None
        finally:
            db.close()

    @staticmethod
    def get_by_mobile(mobile):
        """Fetch an active Student by mobile number. Returns None if not found."""
        db = get_db()
        try:
            row = db.execute(
                "SELECT * FROM students WHERE mobile = ? AND is_active = 1",
                (mobile,)
            ).fetchone()
            return Student(row) if row else None
        finally:
            db.close()

    @staticmethod
    def get_by_identifier(identifier):
        """
        Auto-detect whether identifier is an email or mobile number
        and return the matching active Student. Returns None if not found.
        """
        import re
        if re.fullmatch(r"\d{10}", identifier.strip()):
            return Student.get_by_mobile(identifier.strip())
        return Student.get_by_email(identifier.strip())

    @staticmethod
    def get_all(active_only=True):
        """Return a list of all Students (optionally only active ones)."""
        db = get_db()
        try:
            query = "SELECT * FROM students"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY created_at DESC"
            rows = db.execute(query).fetchall()
            return [Student(r) for r in rows]
        finally:
            db.close()

    @staticmethod
    def email_exists(email):
        """Return True if an account with this email already exists."""
        db = get_db()
        try:
            row = db.execute(
                "SELECT id FROM students WHERE email = ?", (email,)
            ).fetchone()
            return row is not None
        finally:
            db.close()

    @staticmethod
    def mobile_exists(mobile):
        """Return True if an account with this mobile already exists."""
        db = get_db()
        try:
            row = db.execute(
                "SELECT id FROM students WHERE mobile = ?", (mobile,)
            ).fetchone()
            return row is not None
        finally:
            db.close()


    # ── UPDATE ────────────────────────────────────────────────

    @staticmethod
    def update_profile(student_id, name, course):
        """Update the student's display name and course."""
        db = get_db()
        try:
            db.execute(
                "UPDATE students SET name = ?, course = ? WHERE id = ?",
                (name, course, student_id)
            )
            db.commit()
            return Student.get_by_id(student_id)
        finally:
            db.close()

    @staticmethod
    def update_password(student_id, new_password_hash):
        """Replace the stored password hash."""
        db = get_db()
        try:
            db.execute(
                "UPDATE students SET password_hash = ? WHERE id = ?",
                (new_password_hash, student_id)
            )
            db.commit()
        finally:
            db.close()

    @staticmethod
    def update_last_login(student_id):
        """Stamp the current UTC time as last_login."""
        db = get_db()
        try:
            db.execute(
                "UPDATE students SET last_login = ? WHERE id = ?",
                (datetime.utcnow(), student_id)
            )
            db.commit()
        finally:
            db.close()


    # ── DELETE (soft) ─────────────────────────────────────────

    @staticmethod
    def deactivate(student_id):
        """
        Soft-delete: set is_active = 0.
        The row stays in the database for data integrity
        (daily_logs, performance, recommendations still reference it).
        """
        db = get_db()
        try:
            db.execute(
                "UPDATE students SET is_active = 0 WHERE id = ?",
                (student_id,)
            )
            db.commit()
        finally:
            db.close()

    @staticmethod
    def reactivate(student_id):
        """Re-enable a previously deactivated account."""
        db = get_db()
        try:
            db.execute(
                "UPDATE students SET is_active = 1 WHERE id = ?",
                (student_id,)
            )
            db.commit()
        finally:
            db.close()