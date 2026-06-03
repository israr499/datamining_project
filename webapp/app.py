

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
import sys
import secrets
import numpy as np
import pandas as pd
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import auth_bp, login_required, get_current_user, is_logged_in
from feature_extractor import extract_features_from_raw, generate_sample_pattern
from model_loader import load_models, predict_household_anomaly, is_models_loaded
from risk_forecasting import forecast_household_future_risk

from detection_storage import (
    save_detection,
    get_recent_detections,
    get_detection_summary,
    get_household_latest,
    get_household_history,
    get_household_stats,
    get_household_trend,

    create_investigation_case,
    get_all_investigation_cases,
    get_investigation_case_by_id,
    update_investigation_status,
    add_investigation_note,
    get_case_notes,
    get_investigation_summary,
    get_case_by_household
)


app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_COOKIE_EXPIRES"] = None

CORS(app)
app.register_blueprint(auth_bp)


print("=" * 60)
print("Starting ElectroGuard Web Application...")
print("=" * 60)

models_loaded = load_models()

if models_loaded:
    print("✅ Models loaded successfully!")
else:
    print("⚠️ Models not loaded. Prediction will use demo mode.")

print("=" * 60)




@app.route("/")
@login_required
def index():
    user = get_current_user()
    return render_template("index.html", user=user)


@app.route("/predict")
@login_required
def predict_page():
    user = get_current_user()
    return render_template("predict.html", user=user)


@app.route("/analytics")
@login_required
def analytics_page():
    user = get_current_user()
    return render_template("analytics.html", user=user)


@app.route("/household/<household_id>")
@login_required
def household_detail_page(household_id):
    user = get_current_user()
    return render_template(
        "household_detail.html",
        user=user,
        household_id=household_id
    )


@app.route("/investigations")
@login_required
def investigations_page():
    user = get_current_user()
    return render_template("investigations.html", user=user)


@app.route("/investigation/<case_id>")
@login_required
def investigation_detail_page(case_id):
    user = get_current_user()
    return render_template(
        "investigation_detail.html",
        user=user,
        case_id=case_id
    )



@app.route("/api/household/<household_id>", methods=["GET"])
@login_required
def api_household_detail(household_id):
    try:
        latest = get_household_latest(household_id)
        history = get_household_history(household_id, limit=30)
        stats = get_household_stats(household_id)
        trend = get_household_trend(household_id, limit=30)
        active_case = get_case_by_household(household_id)

        if not latest:
            return jsonify({
                "success": False,
                "message": "No detection records found for this household."
            }), 404

        confidence = float(latest.get("confidence", 0))
        is_anomaly = bool(latest.get("is_anomaly", 0))

        if not is_anomaly:
            risk_level = "Normal"
        elif confidence >= 85:
            risk_level = "Critical Risk"
        elif confidence >= 75:
            risk_level = "High Risk"
        else:
            risk_level = "Medium Risk"

        return jsonify({
            "success": True,
            "household_id": household_id,
            "latest": latest,
            "history": history,
            "stats": stats,
            "trend": trend,
            "risk_level": risk_level,
            "active_case": active_case
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500




@app.route("/api/forecast/<household_id>", methods=["GET"])
@login_required
def api_household_forecast(household_id):
    try:
        history = get_household_history(household_id, limit=30)

        forecast = forecast_household_future_risk(
            household_id=household_id,
            history=history
        )

        return jsonify(forecast)

    except Exception as e:
        return jsonify({
            "success": False,
            "household_id": household_id,
            "message": str(e)
        }), 500


@app.route("/api/forecast/top-risk", methods=["GET"])
@login_required
def api_top_future_risk():
    try:
        limit = int(request.args.get("limit", 10))
        recent_rows = get_recent_detections(limit=500)

        household_ids = []

        for row in recent_rows:
            hid = row.get("household_id")
            if hid and hid not in household_ids:
                household_ids.append(hid)

        forecasts = []

        for household_id in household_ids:
            history = get_household_history(household_id, limit=30)

            forecast = forecast_household_future_risk(
                household_id=household_id,
                history=history
            )

            if forecast.get("success"):
                latest = get_household_latest(household_id)

                forecasts.append({
                    "household_id": household_id,
                    "future_risk_probability": forecast.get("future_risk_probability", 0),
                    "forecast_level": forecast.get("forecast_level", "Unknown"),
                    "forecast_window": forecast.get("forecast_window", "Unknown"),
                    "risk_trend": forecast.get("risk_trend", "Unknown"),
                    "recommended_action": forecast.get("recommended_action", ""),
                    "current_anomaly_type": latest.get("anomaly_type", "Unknown") if latest else "Unknown",
                    "current_confidence": latest.get("confidence", 0) if latest else 0
                })

        forecasts = sorted(
            forecasts,
            key=lambda x: x["future_risk_probability"],
            reverse=True
        )[:limit]

        very_high = sum(1 for f in forecasts if f["future_risk_probability"] >= 85)
        high = sum(1 for f in forecasts if 70 <= f["future_risk_probability"] < 85)
        moderate = sum(1 for f in forecasts if 50 <= f["future_risk_probability"] < 70)
        low = sum(1 for f in forecasts if f["future_risk_probability"] < 50)

        avg_risk = 0
        if forecasts:
            avg_risk = sum(f["future_risk_probability"] for f in forecasts) / len(forecasts)

        return jsonify({
            "success": True,
            "top_forecasts": forecasts,
            "summary": {
                "total_forecasted_households": len(forecasts),
                "average_future_risk": round(avg_risk, 2),
                "very_high_future_risk": very_high,
                "high_future_risk": high,
                "moderate_future_risk": moderate,
                "low_future_risk": low
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================
# INVESTIGATION APIs
# ============================================

@app.route("/api/investigations", methods=["GET"])
@login_required
def api_get_investigations():
    try:
        status = request.args.get("status", "All")
        limit = int(request.args.get("limit", 100))

        cases = get_all_investigation_cases(limit=limit, status=status)
        summary = get_investigation_summary()

        return jsonify({
            "success": True,
            "cases": cases,
            "summary": summary
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/investigations/create", methods=["POST"])
@login_required
def api_create_investigation():
    try:
        data = request.get_json() or {}

        household_id = data.get("household_id", "").strip()
        detection_id = data.get("detection_id", None)
        assigned_to = data.get("assigned_to", "Unassigned")
        description = data.get("description", None)

        user = get_current_user()
        created_by = "System User"

        if user:
            created_by = user.get("full_name") or user.get("username") or "System User"

        if not household_id:
            return jsonify({
                "success": False,
                "message": "household_id is required."
            }), 400

        result = create_investigation_case(
            household_id=household_id,
            detection_id=detection_id,
            assigned_to=assigned_to,
            created_by=created_by,
            description=description
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/investigations/<case_id>", methods=["GET"])
@login_required
def api_get_investigation_detail(case_id):
    try:
        case = get_investigation_case_by_id(case_id)

        if not case:
            return jsonify({
                "success": False,
                "message": "Investigation case not found."
            }), 404

        household_id = case.get("household_id")

        household_latest = get_household_latest(household_id)
        household_history = get_household_history(household_id, limit=20)
        household_stats = get_household_stats(household_id)
        household_trend = get_household_trend(household_id, limit=20)
        notes = get_case_notes(case_id)
        forecast = forecast_household_future_risk(household_id, household_history)

        return jsonify({
            "success": True,
            "case": case,
            "household_latest": household_latest,
            "household_history": household_history,
            "household_stats": household_stats,
            "household_trend": household_trend,
            "forecast": forecast,
            "notes": notes
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/investigations/<case_id>/status", methods=["POST"])
@login_required
def api_update_investigation_status(case_id):
    try:
        data = request.get_json() or {}

        status = data.get("status", "").strip()
        assigned_to = data.get("assigned_to", None)

        if not status:
            return jsonify({
                "success": False,
                "message": "Status is required."
            }), 400

        result = update_investigation_status(
            case_id=case_id,
            status=status,
            assigned_to=assigned_to
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/investigations/<case_id>/notes", methods=["GET"])
@login_required
def api_get_investigation_notes(case_id):
    try:
        case = get_investigation_case_by_id(case_id)

        if not case:
            return jsonify({
                "success": False,
                "message": "Investigation case not found."
            }), 404

        notes = get_case_notes(case_id)

        return jsonify({
            "success": True,
            "notes": notes
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/investigations/<case_id>/notes", methods=["POST"])
@login_required
def api_add_investigation_note(case_id):
    try:
        data = request.get_json() or {}

        note_text = data.get("note_text", "").strip()

        user = get_current_user()
        added_by = "System User"

        if user:
            added_by = user.get("full_name") or user.get("username") or "System User"

        if not note_text:
            return jsonify({
                "success": False,
                "message": "Note cannot be empty."
            }), 400

        result = add_investigation_note(
            case_id=case_id,
            note_text=note_text,
            added_by=added_by
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/investigations/summary", methods=["GET"])
@login_required
def api_investigation_summary():
    try:
        summary = get_investigation_summary()

        return jsonify({
            "success": True,
            "summary": summary
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================
# PREDICTION API
# ============================================

@app.route("/api/predict", methods=["POST"])
@login_required
def api_predict():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data received."}), 400

        if "consumption" in data:
            consumption = data["consumption"]
        else:
            consumption = generate_sample_pattern(data.get("pattern", "normal"))

        if len(consumption) != 96:
            return jsonify({"error": f"Expected 96 readings, got {len(consumption)}"}), 400

        household_id = data.get("household_id", "Manual_Input")
        consumption = np.array(consumption, dtype=float)

        features = extract_features_from_raw(consumption)

        if is_models_loaded():
            result = predict_household_anomaly(features)
        else:
            result = demo_prediction(consumption, features)

        total_consumption = float(np.sum(consumption))
        avg_consumption = float(np.mean(consumption))
        peak_consumption = float(np.max(consumption))
        zero_count = int(np.sum(consumption < 0.1))

        result["consumption_summary"] = {
            "total": total_consumption,
            "avg": avg_consumption,
            "peak": peak_consumption,
            "peak_hour": float(np.argmax(consumption) / 4),
            "min": float(np.min(consumption)),
            "zero_count": zero_count
        }

        hourly_data = []

        for hour in range(24):
            start_idx = hour * 4
            end_idx = start_idx + 4
            hourly_avg = np.mean(consumption[start_idx:end_idx])

            hourly_data.append({
                "hour": hour,
                "consumption": float(hourly_avg),
                "label": f"{hour:02d}:00"
            })

        result["hourly_data"] = hourly_data

        save_detection(
            household_id=household_id,
            prediction_label=result.get("prediction_label", "Unknown"),
            is_anomaly=result.get("is_anomaly", False),
            anomaly_type=result.get("anomaly_type", "Unknown"),
            confidence=result.get("confidence_percent", result.get("confidence", 0)),
            total_consumption=total_consumption,
            avg_consumption=avg_consumption,
            peak_consumption=peak_consumption,
            zero_intervals=zero_count,
            model_votes=result.get("voting", "")
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/batch_predict", methods=["POST"])
@login_required
def api_batch_predict():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        df = pd.read_csv(file)

        consumption_cols = [
            col for col in df.columns
            if "interval" in col.lower() or str(col).isdigit()
        ]

        if len(consumption_cols) < 96:
            return jsonify({
                "error": f"Expected 96 consumption columns, got {len(consumption_cols)}"
            }), 400

        results = []

        for idx, row in df.iterrows():
            household_id = row.get("household_id", f"CSV_Row_{idx + 1}")
            consumption = row[consumption_cols[:96]].values.astype(float)

            features = extract_features_from_raw(consumption)

            if is_models_loaded():
                pred = predict_household_anomaly(features)
            else:
                pred = demo_prediction(consumption, features)

            total_consumption = float(np.sum(consumption))
            avg_consumption = float(np.mean(consumption))
            peak_consumption = float(np.max(consumption))
            zero_count = int(np.sum(consumption < 0.1))
            confidence = float(pred.get("confidence_percent", pred.get("confidence", 0)))

            save_detection(
                household_id=household_id,
                prediction_label=pred.get("prediction_label", "Unknown"),
                is_anomaly=pred.get("is_anomaly", False),
                anomaly_type=pred.get("anomaly_type", "Unknown"),
                confidence=confidence,
                total_consumption=total_consumption,
                avg_consumption=avg_consumption,
                peak_consumption=peak_consumption,
                zero_intervals=zero_count,
                model_votes=pred.get("voting", "")
            )

            results.append({
                "household_id": household_id,
                "is_anomaly": bool(pred.get("is_anomaly", False)),
                "confidence": confidence,
                "confidence_percent": confidence,
                "risk_level": pred.get("risk_level", "Normal"),
                "severity_score": float(pred.get("severity_score", 0)),
                "inspection_priority": pred.get("inspection_priority", "No inspection required"),
                "anomaly_type": pred.get("anomaly_type", "Unknown"),
                "suspicious_features": pred.get("suspicious_features", []),
                "rule_risk_points": pred.get("rule_risk_points", 0),
                "total_consumption": total_consumption
            })

        return jsonify({
            "success": True,
            "total_households": len(results),
            "anomalies_detected": sum(1 for r in results if r["is_anomaly"]),
            "results": results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate_sample", methods=["GET"])
@login_required
def api_generate_sample():
    try:
        pattern_type = request.args.get("pattern", "normal")
        consumption = generate_sample_pattern(pattern_type)
        features = extract_features_from_raw(consumption)

        return jsonify({
            "consumption": consumption,
            "features": features,
            "pattern_type": pattern_type
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================
# ANALYTICS APIs
# ============================================

@app.route("/api/analytics/stats", methods=["GET"])
@login_required
def api_analytics_stats():
    try:
        processed_dir = os.path.join(os.path.dirname(__file__), "../data/processed")
        models_dir = os.path.join(os.path.dirname(__file__), "../data/models")

        stats_path = os.path.join(processed_dir, "household_statistics.csv")
        labels_path = os.path.join(processed_dir, "y_labels.csv")
        metrics_path = os.path.join(processed_dir, "model_metrics.json")
        metadata_path = os.path.join(models_dir, "model_metadata.json")

        total_households = 370
        total_energy = 0.0
        suspicious_records = 0
        model_accuracy = 0.0
        anomaly_threshold = 0.0

        if os.path.exists(stats_path):
            df_stats = pd.read_csv(stats_path)
            total_households = int(len(df_stats))

            if "total_consumption" in df_stats.columns:
                total_energy = float(df_stats["total_consumption"].sum())
            elif "total_daily" in df_stats.columns:
                total_energy = float(df_stats["total_daily"].sum())

        if os.path.exists(labels_path):
            y = pd.read_csv(labels_path)

            if y.shape[1] == 1:
                suspicious_records = int(y.iloc[:, 0].sum())
            elif "is_anomaly" in y.columns:
                suspicious_records = int(y["is_anomaly"].sum())
            elif "label" in y.columns:
                suspicious_records = int(y["label"].sum())

        if os.path.exists(metrics_path):
            with open(metrics_path, "r") as f:
                metrics = json.load(f)

            if "random_forest" in metrics:
                model_accuracy = float(metrics["random_forest"].get("accuracy", 0)) * 100

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            anomaly_threshold = float(metadata.get("anomaly_threshold", 0.0))

        stored_summary = get_detection_summary()
        investigation_summary = get_investigation_summary()

        # Deployment demo fallback values
        if suspicious_records == 0:
            suspicious_records = 150

        if total_energy == 0:
            total_energy = 27400000000

        return jsonify({
            "total_households": total_households,
            "suspicious_records": suspicious_records,
            "stored_predictions": stored_summary["total_predictions"],
            "stored_suspicious_predictions": stored_summary["suspicious_predictions"],
            "total_energy": total_energy,
            "stored_total_energy": stored_summary["stored_total_energy"],
            "model_accuracy": model_accuracy,
            "anomaly_threshold": anomaly_threshold,
            "system_status": "Active" if is_models_loaded() else "Demo Mode",
            "active_models": "5/5" if is_models_loaded() else "0/5",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "investigation_summary": investigation_summary
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/clusters", methods=["GET"])
@login_required
def api_analytics_clusters():
    try:
        cluster_path = os.path.join(
            os.path.dirname(__file__),
            "../data/processed/cluster_profiles.csv"
        )

        clusters = []

        if os.path.exists(cluster_path):
            df_clusters = pd.read_csv(cluster_path)

            for _, row in df_clusters.iterrows():
                cluster_id = int(row.get("cluster", row.get("Cluster", len(clusters))))
                size = int(row.get("size", row.get("count", row.get("Size", 0))))
                risk_level = row.get("risk_level", row.get("Risk Level", "N/A"))

                clusters.append({
                    "cluster": cluster_id,
                    "size": size,
                    "risk_level": str(risk_level)
                })

        if not clusters:
            clusters = [
                {"cluster": 0, "size": 850, "risk_level": "Low"},
                {"cluster": 1, "size": 620, "risk_level": "Medium"},
                {"cluster": 2, "size": 430, "risk_level": "High"},
                {"cluster": 3, "size": 300, "risk_level": "Very High"}
            ]

        return jsonify({"clusters": clusters})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/hourly_pattern", methods=["GET"])
@login_required
def api_analytics_hourly_pattern():
    try:
        pattern_values = {
            0: 0.20, 1: 0.18, 2: 0.17, 3: 0.16, 4: 0.18, 5: 0.25,
            6: 0.45, 7: 0.75, 8: 0.95, 9: 1.12,
            10: 0.48, 11: 0.45, 12: 0.44, 13: 0.42, 14: 0.42, 15: 0.43,
            16: 0.55, 17: 0.85, 18: 1.00, 19: 1.15,
            20: 0.55, 21: 0.52, 22: 0.28, 23: 0.24
        }

        hourly_pattern = []

        for hour in range(24):
            hourly_pattern.append({
                "hour": hour,
                "label": f"{hour:02d}:00",
                "consumption": pattern_values[hour]
            })

        return jsonify({"hourly_pattern": hourly_pattern})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/recent_activity", methods=["GET"])
@login_required
def api_recent_activity():
    try:
        rows = get_recent_detections(limit=10)
        activities = []

        for row in rows:
            confidence = float(row.get("confidence", 0))
            is_anomaly = bool(row.get("is_anomaly", 0))

            if is_anomaly:
                status = "High Risk" if confidence >= 80 else "Medium Risk"
            else:
                status = "Normal"

            activities.append({
                "household_id": row.get("household_id", "Unknown"),
                "anomaly_type": row.get("anomaly_type", "Unknown"),
                "confidence": confidence,
                "status": status
            })

        if not activities:
            activities = [{
                "household_id": "No predictions yet",
                "anomaly_type": "Run a prediction first",
                "confidence": 0,
                "status": "Normal"
            }]

        return jsonify({"activities": activities})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/model_metrics", methods=["GET"])
@login_required
def api_model_metrics():
    try:
        metrics_path = os.path.join(
            os.path.dirname(__file__),
            "../data/processed/model_metrics.json"
        )

        if not os.path.exists(metrics_path):
            return jsonify({"error": "model_metrics.json not found"}), 404

        with open(metrics_path, "r") as f:
            metrics = json.load(f)

        return jsonify({"metrics": metrics})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/feature_importance", methods=["GET"])
@login_required
def api_feature_importance():
    try:
        importance_path = os.path.join(
            os.path.dirname(__file__),
            "../data/processed/feature_importance_values.csv"
        )

        if not os.path.exists(importance_path):
            return jsonify({"error": "feature_importance_values.csv not found"}), 404

        df = pd.read_csv(importance_path).head(10)

        return jsonify({
            "features": df["feature"].tolist(),
            "importance": df["importance"].astype(float).tolist()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/confusion_matrix", methods=["GET"])
@login_required
def api_confusion_matrix():
    try:
        metrics_path = os.path.join(
            os.path.dirname(__file__),
            "../data/processed/model_metrics.json"
        )

        if not os.path.exists(metrics_path):
            return jsonify({"error": "model_metrics.json not found"}), 404

        with open(metrics_path, "r") as f:
            metrics = json.load(f)

        rf = metrics.get("random_forest", {})
        matrix = rf.get("confusion_matrix", [[0, 0], [0, 0]])

        return jsonify({"confusion_matrix": matrix})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/risk_distribution", methods=["GET"])
@login_required
def api_risk_distribution():
    try:
        rows = get_recent_detections(limit=500)

        counts = {
            "Normal": 0,
            "Medium Risk": 0,
            "High Risk": 0,
            "Critical Risk": 0
        }

        for row in rows:
            confidence = float(row.get("confidence", 0))
            is_anomaly = bool(row.get("is_anomaly", 0))

            if not is_anomaly:
                counts["Normal"] += 1
            elif confidence >= 85:
                counts["Critical Risk"] += 1
            elif confidence >= 75:
                counts["High Risk"] += 1
            else:
                counts["Medium Risk"] += 1

        return jsonify({"risk_distribution": counts})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/detection_trend", methods=["GET"])
@login_required
def api_detection_trend():
    try:
        rows = get_recent_detections(limit=200)
        trend = {}

        for row in rows:
            date = str(row.get("created_at", ""))[:10]

            if not date:
                continue

            if date not in trend:
                trend[date] = {"total": 0, "suspicious": 0}

            trend[date]["total"] += 1

            if bool(row.get("is_anomaly", 0)):
                trend[date]["suspicious"] += 1

        dates = sorted(trend.keys())

        return jsonify({
            "dates": dates,
            "total": [trend[d]["total"] for d in dates],
            "suspicious": [trend[d]["suspicious"] for d in dates]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/detection_history", methods=["GET"])
@login_required
def api_detection_history():
    try:
        rows = get_recent_detections(limit=20)
        history = []

        for row in rows:
            confidence = float(row.get("confidence", 0))
            is_anomaly = bool(row.get("is_anomaly", 0))

            if not is_anomaly:
                risk = "Normal"
            elif confidence >= 85:
                risk = "Critical Risk"
            elif confidence >= 75:
                risk = "High Risk"
            else:
                risk = "Medium Risk"

            history.append({
                "household_id": row.get("household_id", "Unknown"),
                "anomaly_type": row.get("anomaly_type", "Unknown"),
                "confidence": confidence,
                "risk_level": risk,
                "total_consumption": float(row.get("total_consumption", 0)),
                "created_at": row.get("created_at", "")
            })

        return jsonify({"history": history})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================
# HEALTH API
# ============================================

@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({
        "status": "running",
        "models_loaded": is_models_loaded(),
        "authenticated": is_logged_in(),
        "timestamp": datetime.now().isoformat()
    })


# ============================================
# DEMO PREDICTION FALLBACK
# ============================================

def demo_prediction(consumption, features):
    anomaly_score = 0.0
    reasons = []
    suspicious_features = []
    rule_risk_points = 0

    if features["zero_proportion"] > 0.15:
        anomaly_score += 0.30
        rule_risk_points += 2
        reasons.append("Many zero or near-zero intervals detected.")
        suspicious_features.append("Zero intervals")

    if features["night_ratio"] < 0.10:
        anomaly_score += 0.25
        rule_risk_points += 2
        reasons.append("Very low night consumption detected.")
        suspicious_features.append("Low night usage")

    if features["load_factor"] < 0.30:
        anomaly_score += 0.25
        rule_risk_points += 2
        reasons.append("Low load factor detected.")
        suspicious_features.append("Low load factor")

    if features["peak_hour"] < 5 or features["peak_hour"] > 22:
        anomaly_score += 0.20
        rule_risk_points += 1
        reasons.append("Peak usage occurs at unusual hours.")
        suspicious_features.append("Unusual peak hour")

    anomaly_score = min(anomaly_score, 1.0)
    is_anomaly = anomaly_score >= 0.60
    confidence_percent = round(anomaly_score * 100, 2)

    if is_anomaly:
        if features["zero_proportion"] > 0.20:
            anomaly_type = "Extended Zero Periods"
        elif features["night_ratio"] < 0.10:
            anomaly_type = "Night Zeroing"
        elif features["load_factor"] < 0.30:
            anomaly_type = "Peak Clipping"
        else:
            anomaly_type = "Unusual Consumption Pattern"
    else:
        anomaly_type = "Normal"

    if not reasons:
        reasons.append("Consumption pattern is within normal expected range.")
        suspicious_features.append("No strong suspicious feature detected")

    severity_score = min(100, round((rule_risk_points / 15) * 100, 2))

    if is_anomaly:
        if confidence_percent >= 85:
            risk_level = "Critical Risk"
        elif confidence_percent >= 75:
            risk_level = "High Risk"
        else:
            risk_level = "Medium Risk"
    else:
        risk_level = "Normal"

    return {
        "is_anomaly": is_anomaly,
        "prediction_label": "Suspicious Consumption Pattern" if is_anomaly else "Normal Consumption Pattern",
        "confidence": confidence_percent,
        "confidence_percent": confidence_percent,
        "anomaly_score": confidence_percent,
        "severity_score": severity_score,
        "risk_level": risk_level,
        "inspection_priority": "Inspect if repeated" if is_anomaly else "No inspection required",
        "anomaly_type": anomaly_type,
        "cluster": 0,
        "distance_to_center": 0,
        "models": {"demo_mode": True},
        "voting": "Demo Mode - Rule Based Detection",
        "rf_probability": 0,
        "rule_risk_points": rule_risk_points,
        "reasons": reasons,
        "suspicious_features": suspicious_features,
        "recommended_action": (
            "Review this household for possible abnormal usage."
            if is_anomaly
            else "No immediate action required."
        ),
        "feature_summary": {
            "total_daily": round(features.get("total_daily", 0), 3),
            "avg_consumption": round(features.get("avg_consumption", 0), 3),
            "max_consumption": round(features.get("max_consumption", 0), 3),
            "min_consumption": round(features.get("min_consumption", 0), 3),
            "night_ratio": round(features.get("night_ratio", 0), 3),
            "zero_proportion": round(features.get("zero_proportion", 0), 3),
            "load_factor": round(features.get("load_factor", 0), 3),
            "cv": round(features.get("cv", 0), 3),
            "peak_hour": round(features.get("peak_hour", 0), 2)
        }
    }


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Route not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ============================================
# RUN APP
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 ElectroGuard Web Application Starting...")
    print("=" * 60)
    print("📱 Access: http://localhost:5000")
    print("🔐 Login: http://localhost:5000/login")
    print("📊 Dashboard: http://localhost:5000/")
    print("🔍 Predict: http://localhost:5000/predict")
    print("📈 Analytics: http://localhost:5000/analytics")
    print("🏠 Household Detail: http://localhost:5000/household/<household_id>")
    print("🚨 Investigations: http://localhost:5000/investigations")
    print("🔮 Forecast API: http://localhost:5000/api/forecast/<household_id>")
    print("⚠️ Press CTRL+C to stop")
    print("=" * 60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000)