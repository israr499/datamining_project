# ============================================
# webapp/detection_storage.py
# Module 4: Store and Retrieve Detection Results
# ============================================

import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "detections.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_detection_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            household_id TEXT,
            prediction_label TEXT,
            is_anomaly INTEGER,
            anomaly_type TEXT,
            confidence REAL,
            total_consumption REAL,
            avg_consumption REAL,
            peak_consumption REAL,
            zero_intervals INTEGER,
            model_votes TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_detection(
    household_id,
    prediction_label,
    is_anomaly,
    anomaly_type,
    confidence,
    total_consumption,
    avg_consumption,
    peak_consumption,
    zero_intervals,
    model_votes
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO detections (
            household_id,
            prediction_label,
            is_anomaly,
            anomaly_type,
            confidence,
            total_consumption,
            avg_consumption,
            peak_consumption,
            zero_intervals,
            model_votes,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        household_id,
        prediction_label,
        int(is_anomaly),
        anomaly_type,
        float(confidence),
        float(total_consumption),
        float(avg_consumption),
        float(peak_consumption),
        int(zero_intervals),
        str(model_votes),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_recent_detections(limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM detections
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_detection_summary():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM detections")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS suspicious FROM detections WHERE is_anomaly = 1")
    suspicious = cursor.fetchone()["suspicious"]

    cursor.execute("SELECT SUM(total_consumption) AS total_energy FROM detections")
    total_energy = cursor.fetchone()["total_energy"]

    conn.close()

    return {
        "total_predictions": total or 0,
        "suspicious_predictions": suspicious or 0,
        "stored_total_energy": total_energy or 0
    }


init_detection_db()