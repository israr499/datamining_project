

import sqlite3
import hashlib
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            email_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT UNIQUE,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Safe upgrade for old users.db files
    if not column_exists(cursor, "users", "email_verified"):
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN email_verified INTEGER DEFAULT 1
        """)
        print("✅ Added email_verified column to existing users table.")

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def create_user(username, email, password, full_name=None, email_verified=0):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        hashed_pw = hash_password(password)

        cursor.execute("""
            INSERT INTO users (username, email, password, full_name, email_verified)
            VALUES (?, ?, ?, ?, ?)
        """, (username, email, hashed_pw, full_name, email_verified))

        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return {
            "success": True,
            "user_id": user_id,
            "message": "User created successfully"
        }

    except sqlite3.IntegrityError as e:
        conn.close()

        error_msg = str(e).lower()

        if "username" in error_msg:
            return {
                "success": False,
                "message": "Username already exists"
            }

        if "email" in error_msg:
            return {
                "success": False,
                "message": "Email already exists"
            }

        return {
            "success": False,
            "message": "Error creating user"
        }


def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, full_name, password, is_active, email_verified
        FROM users
        WHERE username = ? OR email = ?
    """, (username, username))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return {
            "success": False,
            "message": "Invalid username or password"
        }

    if not verify_password(password, user["password"]):
        return {
            "success": False,
            "message": "Invalid username or password"
        }

    if not user["is_active"]:
        return {
            "success": False,
            "message": "Account is disabled"
        }

    if int(user["email_verified"]) != 1:
        return {
            "success": False,
            "message": "Email is not verified. Please verify your email first."
        }

    return {
        "success": True,
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"]
    }


def update_last_login(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users 
        SET last_login = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (user_id,))

    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, full_name, email_verified, created_at, last_login
        FROM users
        WHERE id = ?
    """, (user_id,))

    user = cursor.fetchone()
    conn.close()

    return dict(user) if user else None


def get_user_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, full_name, email_verified, created_at, last_login
        FROM users
        WHERE email = ?
    """, (email,))

    user = cursor.fetchone()
    conn.close()

    return dict(user) if user else None


def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, full_name, email_verified, created_at, last_login
        FROM users
        WHERE username = ?
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    return dict(user) if user else None


def mark_email_verified(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET email_verified = 1
        WHERE id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Email marked as verified"
    }


def mark_email_verified_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET email_verified = 1
        WHERE email = ?
    """, (email,))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated > 0:
        return {
            "success": True,
            "message": "Email marked as verified"
        }

    return {
        "success": False,
        "message": "User not found"
    }


def email_exists(email):
    return get_user_by_email(email) is not None


def username_exists(username):
    return get_user_by_username(username) is not None


init_db()