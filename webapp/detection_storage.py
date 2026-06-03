

import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "detections.db")




def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



def init_detection_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Main detection table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            household_id TEXT NOT NULL,
            prediction_label TEXT,
            is_anomaly INTEGER DEFAULT 0,
            anomaly_type TEXT,
            confidence REAL DEFAULT 0,
            total_consumption REAL DEFAULT 0,
            avg_consumption REAL DEFAULT 0,
            peak_consumption REAL DEFAULT 0,
            zero_intervals INTEGER DEFAULT 0,
            model_votes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Investigation cases table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS investigation_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            household_id TEXT NOT NULL,
            detection_id INTEGER,
            risk_level TEXT DEFAULT 'Medium Risk',
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            anomaly_type TEXT,
            confidence REAL DEFAULT 0,
            total_consumption REAL DEFAULT 0,
            zero_intervals INTEGER DEFAULT 0,
            assigned_to TEXT DEFAULT 'Unassigned',
            description TEXT,
            recommended_action TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (detection_id) REFERENCES detections (id)
        )
    """)

    # Investigation notes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS investigation_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            note_text TEXT NOT NULL,
            added_by TEXT DEFAULT 'System User',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES investigation_cases (case_id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Detection + Investigation database initialized successfully!")




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
    model_votes=""
):
    conn = get_db_connection()
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
        1 if is_anomaly else 0,
        anomaly_type,
        float(confidence or 0),
        float(total_consumption or 0),
        float(avg_consumption or 0),
        float(peak_consumption or 0),
        int(zero_intervals or 0),
        model_votes,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    detection_id = cursor.lastrowid
    conn.close()

    return detection_id


def get_recent_detections(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM detections
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_detection_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total_predictions FROM detections")
    total_predictions = cursor.fetchone()["total_predictions"]

    cursor.execute("""
        SELECT COUNT(*) AS suspicious_predictions
        FROM detections
        WHERE is_anomaly = 1
    """)
    suspicious_predictions = cursor.fetchone()["suspicious_predictions"]

    cursor.execute("""
        SELECT COALESCE(SUM(total_consumption), 0) AS stored_total_energy
        FROM detections
    """)
    stored_total_energy = cursor.fetchone()["stored_total_energy"]

    conn.close()

    return {
        "total_predictions": int(total_predictions or 0),
        "suspicious_predictions": int(suspicious_predictions or 0),
        "stored_total_energy": float(stored_total_energy or 0)
    }




def get_household_latest(household_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM detections
        WHERE household_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    """, (household_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_household_history(household_id, limit=30):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM detections
        WHERE household_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    """, (household_id, limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_household_stats(household_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS total_checks,
            SUM(CASE WHEN is_anomaly = 1 THEN 1 ELSE 0 END) AS suspicious_count,
            AVG(confidence) AS avg_confidence,
            MAX(confidence) AS max_confidence,
            AVG(total_consumption) AS avg_total_consumption,
            MAX(total_consumption) AS max_total_consumption,
            AVG(avg_consumption) AS avg_interval_consumption,
            MAX(peak_consumption) AS max_peak_consumption,
            AVG(zero_intervals) AS avg_zero_intervals
        FROM detections
        WHERE household_id = ?
    """, (household_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    total_checks = int(row["total_checks"] or 0)
    suspicious_count = int(row["suspicious_count"] or 0)

    suspicious_rate = 0
    if total_checks > 0:
        suspicious_rate = (suspicious_count / total_checks) * 100

    return {
        "household_id": household_id,
        "total_checks": total_checks,
        "suspicious_count": suspicious_count,
        "suspicious_rate": round(suspicious_rate, 2),
        "avg_confidence": round(float(row["avg_confidence"] or 0), 2),
        "max_confidence": round(float(row["max_confidence"] or 0), 2),
        "avg_total_consumption": round(float(row["avg_total_consumption"] or 0), 2),
        "max_total_consumption": round(float(row["max_total_consumption"] or 0), 2),
        "avg_interval_consumption": round(float(row["avg_interval_consumption"] or 0), 3),
        "max_peak_consumption": round(float(row["max_peak_consumption"] or 0), 3),
        "avg_zero_intervals": round(float(row["avg_zero_intervals"] or 0), 2)
    }


def get_household_trend(household_id, limit=30):
    history = get_household_history(household_id, limit=limit)
    history = list(reversed(history))

    labels = []
    confidence_values = []
    consumption_values = []
    anomaly_flags = []

    for row in history:
        labels.append(row.get("created_at", ""))
        confidence_values.append(float(row.get("confidence", 0) or 0))
        consumption_values.append(float(row.get("total_consumption", 0) or 0))
        anomaly_flags.append(int(row.get("is_anomaly", 0) or 0))

    return {
        "labels": labels,
        "confidence": confidence_values,
        "total_consumption": consumption_values,
        "anomaly_flags": anomaly_flags
    }


# ============================================
# INVESTIGATION CASE HELPERS
# ============================================

def generate_case_id():
    """
    Generate unique case ID like CASE-20260516-0001.
    """
    today = datetime.now().strftime("%Y%m%d")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS count_today
        FROM investigation_cases
        WHERE case_id LIKE ?
    """, (f"CASE-{today}-%",))

    count_today = cursor.fetchone()["count_today"]
    conn.close()

    next_number = int(count_today or 0) + 1
    return f"CASE-{today}-{next_number:04d}"


def calculate_priority(risk_level, confidence):
    """
    Convert risk level/confidence into operational priority.
    """
    risk = str(risk_level or "").lower()
    conf = float(confidence or 0)

    if "critical" in risk or conf >= 85:
        return "Critical"

    if "high" in risk or conf >= 75:
        return "High"

    if "medium" in risk or conf >= 60:
        return "Medium"

    return "Low"


def get_risk_level_from_detection(detection):
    """
    Estimate risk level from detection record.
    """
    if not detection:
        return "Medium Risk"

    confidence = float(detection.get("confidence", 0) or 0)
    is_anomaly = bool(detection.get("is_anomaly", 0))

    if not is_anomaly:
        return "Normal"

    if confidence >= 85:
        return "Critical Risk"

    if confidence >= 75:
        return "High Risk"

    return "Medium Risk"


def get_recommended_action_from_detection(detection):
    """
    Generate recommended action based on anomaly type and risk.
    """
    if not detection:
        return "Review detection data before taking action."

    anomaly_type = str(detection.get("anomaly_type", "")).lower()
    confidence = float(detection.get("confidence", 0) or 0)
    zero_intervals = int(detection.get("zero_intervals", 0) or 0)

    if "zero" in anomaly_type or zero_intervals >= 20:
        return "Immediate meter inspection recommended due to extended zero-consumption intervals."

    if confidence >= 85:
        return "Immediate field inspection recommended due to critical suspicious pattern."

    if confidence >= 75:
        return "Schedule field inspection and monitor future consumption readings."

    if confidence >= 60:
        return "Monitor future readings and inspect if suspicious pattern repeats."

    return "No immediate field action required. Continue regular monitoring."


# ============================================
# INVESTIGATION CASE FUNCTIONS
# ============================================

def create_investigation_case(
    household_id,
    detection_id=None,
    assigned_to="Unassigned",
    created_by="System User",
    description=None
):
    """
    Create investigation case for a household.
    If detection_id is not provided, latest detection is used.
    Prevent duplicate OPEN/UNDER REVIEW/FIELD INSPECTION cases for same household.
    """

    latest_detection = None

    if detection_id:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM detections
            WHERE id = ?
            LIMIT 1
        """, (detection_id,))

        row = cursor.fetchone()
        conn.close()

        latest_detection = dict(row) if row else None
    else:
        latest_detection = get_household_latest(household_id)
        detection_id = latest_detection.get("id") if latest_detection else None

    if not latest_detection:
        return {
            "success": False,
            "message": "No detection record found for this household."
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    # Prevent duplicate active case for same household
    cursor.execute("""
        SELECT *
        FROM investigation_cases
        WHERE household_id = ?
        AND status IN ('Open', 'Under Review', 'Field Inspection')
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    """, (household_id,))

    existing_case = cursor.fetchone()

    if existing_case:
        conn.close()
        return {
            "success": True,
            "message": "Active investigation case already exists for this household.",
            "case": dict(existing_case),
            "already_exists": True
        }

    risk_level = get_risk_level_from_detection(latest_detection)
    confidence = float(latest_detection.get("confidence", 0) or 0)
    priority = calculate_priority(risk_level, confidence)
    anomaly_type = latest_detection.get("anomaly_type", "Unknown")
    total_consumption = float(latest_detection.get("total_consumption", 0) or 0)
    zero_intervals = int(latest_detection.get("zero_intervals", 0) or 0)
    recommended_action = get_recommended_action_from_detection(latest_detection)

    if not description:
        description = (
            f"Investigation opened for {household_id}. "
            f"Detected anomaly type: {anomaly_type}. "
            f"Confidence: {confidence:.1f}%."
        )

    case_id = generate_case_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO investigation_cases (
            case_id,
            household_id,
            detection_id,
            risk_level,
            priority,
            status,
            anomaly_type,
            confidence,
            total_consumption,
            zero_intervals,
            assigned_to,
            description,
            recommended_action,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        case_id,
        household_id,
        detection_id,
        risk_level,
        priority,
        "Open",
        anomaly_type,
        confidence,
        total_consumption,
        zero_intervals,
        assigned_to,
        description,
        recommended_action,
        now,
        now
    ))

    cursor.execute("""
        INSERT INTO investigation_notes (
            case_id,
            note_text,
            added_by,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        case_id,
        "Investigation case created automatically from anomaly detection result.",
        created_by,
        now
    ))

    conn.commit()

    cursor.execute("""
        SELECT *
        FROM investigation_cases
        WHERE case_id = ?
        LIMIT 1
    """, (case_id,))

    case_row = cursor.fetchone()
    conn.close()

    return {
        "success": True,
        "message": "Investigation case created successfully.",
        "case": dict(case_row),
        "already_exists": False
    }


def get_all_investigation_cases(limit=100, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if status and status != "All":
        cursor.execute("""
            SELECT *
            FROM investigation_cases
            WHERE status = ?
            ORDER BY
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END,
                created_at DESC
            LIMIT ?
        """, (status, limit))
    else:
        cursor.execute("""
            SELECT *
            FROM investigation_cases
            ORDER BY
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END,
                created_at DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_investigation_case_by_id(case_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM investigation_cases
        WHERE case_id = ?
        LIMIT 1
    """, (case_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_case_by_household(household_id):
    """
    Get latest active case for a household.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM investigation_cases
        WHERE household_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    """, (household_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def update_investigation_status(case_id, status, assigned_to=None):
    """
    Update investigation case status.
    If status is resolved/confirmed/false alarm, close the case.
    """

    valid_statuses = [
        "Open",
        "Under Review",
        "Field Inspection",
        "Confirmed Theft",
        "False Alarm",
        "Resolved"
    ]

    if status not in valid_statuses:
        return {
            "success": False,
            "message": f"Invalid status. Allowed statuses: {', '.join(valid_statuses)}"
        }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    close_statuses = ["Confirmed Theft", "False Alarm", "Resolved"]
    closed_at = now if status in close_statuses else None

    conn = get_db_connection()
    cursor = conn.cursor()

    if assigned_to is not None:
        cursor.execute("""
            UPDATE investigation_cases
            SET status = ?,
                assigned_to = ?,
                updated_at = ?,
                closed_at = ?
            WHERE case_id = ?
        """, (status, assigned_to, now, closed_at, case_id))
    else:
        cursor.execute("""
            UPDATE investigation_cases
            SET status = ?,
                updated_at = ?,
                closed_at = ?
            WHERE case_id = ?
        """, (status, now, closed_at, case_id))

    if cursor.rowcount == 0:
        conn.close()
        return {
            "success": False,
            "message": "Investigation case not found."
        }

    cursor.execute("""
        INSERT INTO investigation_notes (
            case_id,
            note_text,
            added_by,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        case_id,
        f"Case status updated to: {status}.",
        "System User",
        now
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Investigation status updated successfully."
    }


def add_investigation_note(case_id, note_text, added_by="System User"):
    if not note_text or not note_text.strip():
        return {
            "success": False,
            "message": "Note cannot be empty."
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT case_id
        FROM investigation_cases
        WHERE case_id = ?
        LIMIT 1
    """, (case_id,))

    case_exists = cursor.fetchone()

    if not case_exists:
        conn.close()
        return {
            "success": False,
            "message": "Investigation case not found."
        }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO investigation_notes (
            case_id,
            note_text,
            added_by,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        case_id,
        note_text.strip(),
        added_by,
        now
    ))

    cursor.execute("""
        UPDATE investigation_cases
        SET updated_at = ?
        WHERE case_id = ?
    """, (now, case_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Investigation note added successfully."
    }


def get_case_notes(case_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM investigation_notes
        WHERE case_id = ?
        ORDER BY created_at DESC, id DESC
    """, (case_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_investigation_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total_cases FROM investigation_cases")
    total_cases = cursor.fetchone()["total_cases"]

    cursor.execute("""
        SELECT COUNT(*) AS open_cases
        FROM investigation_cases
        WHERE status IN ('Open', 'Under Review', 'Field Inspection')
    """)
    open_cases = cursor.fetchone()["open_cases"]

    cursor.execute("""
        SELECT COUNT(*) AS critical_cases
        FROM investigation_cases
        WHERE priority = 'Critical'
        AND status IN ('Open', 'Under Review', 'Field Inspection')
    """)
    critical_cases = cursor.fetchone()["critical_cases"]

    cursor.execute("""
        SELECT COUNT(*) AS resolved_cases
        FROM investigation_cases
        WHERE status IN ('Confirmed Theft', 'False Alarm', 'Resolved')
    """)
    resolved_cases = cursor.fetchone()["resolved_cases"]

    conn.close()

    return {
        "total_cases": int(total_cases or 0),
        "open_cases": int(open_cases or 0),
        "critical_cases": int(critical_cases or 0),
        "resolved_cases": int(resolved_cases or 0)
    }


# ============================================
# INITIALIZE DATABASE WHEN MODULE LOADS
# ============================================

init_detection_db()