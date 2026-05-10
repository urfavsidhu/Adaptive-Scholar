import sqlite3
from flask import current_app, g

def get_db():
    """Return a database connection for the current request context."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Create all tables if they do not exist."""
    db = sqlite3.connect(current_app.config["DATABASE_PATH"])
    db.row_factory = sqlite3.Row
    db.executescript("""
        -- Students (auth)
        CREATE TABLE IF NOT EXISTS students (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE,
            mobile        TEXT    UNIQUE,
            password_hash TEXT    NOT NULL,
            course        TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login    DATETIME,
            is_active     BOOLEAN DEFAULT 1
        );

        -- Daily study logs
        CREATE TABLE IF NOT EXISTS daily_logs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id       INTEGER NOT NULL,
            hours_studied    REAL    NOT NULL,
            difficulty       INTEGER NOT NULL,
            plan_completed   BOOLEAN NOT NULL,
            exam_soon        BOOLEAN NOT NULL,
            log_date         DATE    DEFAULT (DATE('now')),
            FOREIGN KEY (student_id) REFERENCES students(id)
        );

        -- Subject performance
        CREATE TABLE IF NOT EXISTS performance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            subject     TEXT    NOT NULL,
            score       REAL    NOT NULL,
            topic       TEXT,
            quiz_date   DATE    DEFAULT (DATE('now')),
            FOREIGN KEY (student_id) REFERENCES students(id)
        );

        -- AI recommendations history
        CREATE TABLE IF NOT EXISTS recommendations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id      INTEGER NOT NULL,
            recommendation  TEXT    NOT NULL,
            label           TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        );
    """)
    db.commit()
    db.close()