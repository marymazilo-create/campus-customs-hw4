"""Accounts and login for Campus Customs (MGT 409 HW 4, Problem 4).

Passwords are never stored. We store a salted, slow hash in users.password_hash:

    pbkdf2_sha256$<salt>$<hash>

  - function:   PBKDF2-HMAC-SHA256
  - iterations: 120,000
  - salt:       16 random hex characters, used as UTF-8 text (same as the seed users)
  - hash:       32-byte result written as 64 hex characters

Sign-up and login share hash_password() below, so they always use the same function,
salt handling and iteration count. Login never "un-hashes" anything: it reads the salt
out of the stored string, re-hashes what was typed with that same salt, and compares
the two results in constant time.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 8          # 8 random bytes -> 16 hex characters
MIN_PASSWORD_LEN = 8
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- hashing (shared by sign-up and login) ----------

def _pbkdf2(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return digest.hex()


def hash_password(password: str, salt: str | None = None) -> str:
    """Sign-up: make a NEW random salt. (Login passes the stored salt instead.)"""
    if salt is None:
        salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${salt}${_pbkdf2(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    """Login: re-hash the typed password with the salt from the stored value and compare."""
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False  # not in our format
    if algorithm != ALGORITHM:
        return False
    typed = _pbkdf2(password, salt)  # same function, same salt, same iterations
    return hmac.compare_digest(typed, expected)  # constant-time compare


# A fixed dummy hash so a login for an unknown email takes as long as a real one
# (otherwise response time would reveal which emails have accounts).
_DUMMY_HASH = hash_password("not-a-real-password", salt="0" * (SALT_BYTES * 2))


# ---------- sessions ----------

def ensure_tables(conn: sqlite3.Connection) -> None:
    """Login sessions: a random token per login, so the browser never holds the password."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
               token TEXT PRIMARY KEY,
               user_id INTEGER NOT NULL,
               created_at TEXT NOT NULL DEFAULT (datetime('now')),
               FOREIGN KEY (user_id) REFERENCES users(id)
           )"""
    )
    conn.commit()


def new_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    conn.commit()
    return token


def user_for_token(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    return conn.execute(
        """SELECT u.id, u.first_name, u.last_name, u.name, u.email, u.created_at
           FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?""",
        (token,),
    ).fetchone()


def end_session(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()


# ---------- account actions ----------

class AuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user(conn: sqlite3.Connection, first: str, last: str, email: str, password: str, confirm: str) -> int:
    first, last, email = first.strip(), last.strip(), normalize_email(email)
    if not first or not last:
        raise AuthError("Please enter your first and last name.")
    if not EMAIL_RE.match(email):
        raise AuthError("Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LEN:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    if password != confirm:
        raise AuthError("Passwords don't match.")
    exists = conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone()
    if exists:
        raise AuthError("An account with that email already exists. Try logging in.", 409)
    cur = conn.execute(
        "INSERT INTO users (name, first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?, ?)",
        (f"{first} {last}", first, last, email, hash_password(password)),
    )
    conn.commit()
    return int(cur.lastrowid)


def login(conn: sqlite3.Connection, email: str, password: str) -> int:
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE lower(email) = ?", (normalize_email(email),)
    ).fetchone()
    stored = row["password_hash"] if row else _DUMMY_HASH
    ok = verify_password(password, stored)
    if not row or not ok:
        # Same message either way, so the form doesn't reveal which emails have accounts.
        raise AuthError("Email or password is incorrect.", 401)
    return int(row["id"])
