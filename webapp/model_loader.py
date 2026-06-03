

import os
import joblib
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist


_model_package = None
_models_loaded = False


def load_models():
    global _model_package, _models_loaded

    try:
        model_path = os.path.join(
            os.path.dirname(__file__),
            "../data/models/model_package.pkl"
        )

        if os.path.exists(model_path):
            _model_package = joblib.load(model_path)
            _models_loaded = True
            print("✅ Model package loaded successfully.")
            return True

        print("⚠️ model_package.pkl not found. Trying individual models...")
        return load_individual_models()

    except Exception as e:
        print(f"❌ Error loading model package: {e}")
        _model_package = None
        _models_loaded = False
        return False


def load_individual_models():
    global _model_package, _models_loaded

    base_path = os.path.join(os.path.dirname(__file__), "../data/models")

    try:
        _model_package = {
            "scaler": joblib.load(os.path.join(base_path, "scaler.pkl")),
            "kmeans": joblib.load(os.path.join(base_path, "kmeans_model.pkl")),
            "anomaly_threshold": joblib.load(os.path.join(base_path, "anomaly_threshold.pkl")),
            "decision_tree": joblib.load(os.path.join(base_path, "decision_tree.pkl")),
            "naive_bayes": joblib.load(os.path.join(base_path, "naive_bayes.pkl")),
            "random_forest": joblib.load(os.path.join(base_path, "random_forest.pkl")),
            "isolation_forest": joblib.load(os.path.join(base_path, "isolation_forest.pkl")),
            "feature_columns": joblib.load(os.path.join(base_path, "feature_columns.pkl")),
        }

        _models_loaded = True
        print("✅ Individual models loaded successfully.")
        return True

    except Exception as e:
        print(f"❌ Error loading individual models: {e}")
        _model_package = None
        _models_loaded = False
        return False


def is_models_loaded():
    return _models_loaded


def get_model(model_name):
    if not _models_loaded:
        load_models()

    if _model_package and model_name in _model_package:
        return _model_package[model_name]

    return None


def prepare_features(features_dict):
    feature_columns = _model_package.get("feature_columns")
    features_df = pd.DataFrame([features_dict])

    if feature_columns is not None:
        for col in feature_columns:
            if col not in features_df.columns:
                features_df[col] = 0

        features_df = features_df[feature_columns]

    scaler = _model_package.get("scaler")

    if scaler is not None:
        features_scaled = scaler.transform(features_df)
    else:
        features_scaled = features_df.values

    return features_df, features_scaled


def calculate_advanced_rules(features_dict):
    """
    Advanced rule-based explanation layer.
    This explains WHY the ML system marked a household as suspicious.
    """

    reasons = []
    suspicious_features = []
    risk_points = 0

    total_daily = features_dict.get("total_daily", 0)
    avg_consumption = features_dict.get("avg_consumption", 0)
    max_consumption = features_dict.get("max_consumption", 0)
    min_consumption = features_dict.get("min_consumption", 0)
    night_ratio = features_dict.get("night_ratio", 1)
    zero_proportion = features_dict.get("zero_proportion", 0)
    load_factor = features_dict.get("load_factor", 1)
    cv = features_dict.get("cv", 0)
    peak_hour = features_dict.get("peak_hour", 12)
    consumption_range = features_dict.get("consumption_range", 0)

    if zero_proportion >= 0.30:
        risk_points += 4
        suspicious_features.append("High zero interval ratio")
        reasons.append("A large part of the day has zero or near-zero consumption, which may indicate meter disconnection or bypass.")

    elif zero_proportion >= 0.15:
        risk_points += 2
        suspicious_features.append("Moderate zero interval ratio")
        reasons.append("Several intervals have zero or near-zero consumption.")

    if night_ratio < 0.05:
        risk_points += 4
        suspicious_features.append("Extremely low night usage")
        reasons.append("Night consumption is almost zero, which can indicate night-time meter tampering.")

    elif night_ratio < 0.15:
        risk_points += 2
        suspicious_features.append("Low night usage")
        reasons.append("Night consumption is unusually low compared with average daily usage.")

    if load_factor < 0.25:
        risk_points += 4
        suspicious_features.append("Very low load factor")
        reasons.append("Very low load factor suggests peak clipping or artificial limitation of meter readings.")

    elif load_factor < 0.35:
        risk_points += 2
        suspicious_features.append("Low load factor")
        reasons.append("Low load factor indicates that peak and average usage are not balanced.")

    if avg_consumption > 0 and max_consumption > avg_consumption * 4:
        risk_points += 3
        suspicious_features.append("Sudden spike")
        reasons.append("A sudden high spike appears compared with the average consumption.")

    if cv > 1.5:
        risk_points += 3
        suspicious_features.append("Very high variability")
        reasons.append("Consumption varies sharply across the day, which may indicate unstable or abnormal usage.")

    elif cv > 1.1:
        risk_points += 1
        suspicious_features.append("High variability")
        reasons.append("Consumption variability is higher than expected.")

    if peak_hour < 5 or peak_hour > 23:
        risk_points += 1
        suspicious_features.append("Unusual peak hour")
        reasons.append("Peak consumption occurred at an unusual time.")

    if total_daily < 5:
        risk_points += 2
        suspicious_features.append("Very low total daily usage")
        reasons.append("Total daily consumption is extremely low.")

    if consumption_range < 0.2 and avg_consumption > 0.2:
        risk_points += 1
        suspicious_features.append("Flat consumption pattern")
        reasons.append("Consumption pattern is unusually flat.")

    if not reasons:
        reasons.append("Consumption pattern is within normal expected range.")
        suspicious_features.append("No strong suspicious feature detected")

    return reasons, suspicious_features, risk_points


def classify_anomaly_type(features_dict):
    night_ratio = features_dict.get("night_ratio", 1)
    zero_proportion = features_dict.get("zero_proportion", 0)
    load_factor = features_dict.get("load_factor", 1)
    cv = features_dict.get("cv", 0)
    max_consumption = features_dict.get("max_consumption", 0)
    avg_consumption = features_dict.get("avg_consumption", 0)
    total_daily = features_dict.get("total_daily", 0)

    if zero_proportion > 0.25:
        return "Extended Zero Periods"

    if night_ratio < 0.10:
        return "Night Zeroing"

    if load_factor < 0.30:
        return "Peak Clipping"

    if avg_consumption > 0 and max_consumption > avg_consumption * 4 and cv > 1.0:
        return "Sudden Spike"

    if total_daily < 8 or avg_consumption < 0.15:
        return "Overall Reduction"

    return "Unusual Consumption Pattern"


def get_risk_level(confidence, is_anomaly):
    if not is_anomaly:
        return "Normal"

    if confidence >= 85:
        return "Critical Risk"

    if confidence >= 75:
        return "High Risk"

    if confidence >= 60:
        return "Medium Risk"

    return "Low Risk"


def get_inspection_priority(risk_level):
    if risk_level == "Critical Risk":
        return "Immediate inspection recommended"

    if risk_level == "High Risk":
        return "High priority inspection recommended"

    if risk_level == "Medium Risk":
        return "Monitor and inspect if repeated"

    if risk_level == "Low Risk":
        return "Low priority monitoring"

    return "No inspection required"


def get_recommended_action(is_anomaly, anomaly_type, confidence, risk_level):
    if not is_anomaly:
        return "No immediate action required. Continue regular monitoring."

    if risk_level == "Critical Risk":
        return f"Immediate field inspection is recommended for possible {anomaly_type.lower()}."

    if risk_level == "High Risk":
        return f"High priority inspection is recommended for possible {anomaly_type.lower()}."

    if risk_level == "Medium Risk":
        return f"Monitor this household and review historical usage for repeated {anomaly_type.lower()}."

    return "Low priority warning. Monitor future readings before inspection."


def predict_household_anomaly(features_dict):
    global _model_package

    if not _models_loaded:
        load_models()

    if not _model_package:
        return {
            "error": "Models not loaded.",
            "is_anomaly": False,
            "prediction_label": "Model Error",
            "confidence": 0,
            "confidence_percent": 0,
            "anomaly_score": 0,
            "anomaly_type": "Unknown",
            "risk_level": "Unknown",
            "severity_score": 0,
            "inspection_priority": "Check model files",
            "reasons": ["Models could not be loaded."],
            "suspicious_features": [],
            "recommended_action": "Check model files in data/models folder."
        }

    features_df, features_scaled = prepare_features(features_dict)

    model_votes = {}
    vote_count = 0
    total_models = 0

    cluster = None
    distance_to_center = 0
    distance_anomaly = False

    kmeans = _model_package.get("kmeans")
    threshold = _model_package.get("anomaly_threshold", 2.0)

    if kmeans is not None:
        total_models += 1
        cluster = int(kmeans.predict(features_scaled)[0])
        distance_to_center = float(np.min(cdist(features_scaled, kmeans.cluster_centers_)))
        distance_anomaly = bool(distance_to_center > threshold)
        model_votes["kmeans_distance"] = distance_anomaly
        vote_count += int(distance_anomaly)

    decision_tree = _model_package.get("decision_tree")

    if decision_tree is not None:
        total_models += 1
        dt_pred = int(decision_tree.predict(features_scaled)[0])
        model_votes["decision_tree"] = bool(dt_pred)
        vote_count += dt_pred

    naive_bayes = _model_package.get("naive_bayes")

    if naive_bayes is not None:
        total_models += 1
        nb_pred = int(naive_bayes.predict(features_scaled)[0])
        model_votes["naive_bayes"] = bool(nb_pred)
        vote_count += nb_pred

    random_forest = _model_package.get("random_forest")
    rf_probability = 0.0

    if random_forest is not None:
        total_models += 1
        rf_pred = int(random_forest.predict(features_scaled)[0])
        model_votes["random_forest"] = bool(rf_pred)
        vote_count += rf_pred

        if hasattr(random_forest, "predict_proba"):
            rf_probability = float(random_forest.predict_proba(features_scaled)[0][1])

    isolation_forest = _model_package.get("isolation_forest")

    if isolation_forest is not None:
        total_models += 1
        iso_raw = isolation_forest.predict(features_scaled)[0]
        iso_pred = int(iso_raw == -1)
        model_votes["isolation_forest"] = bool(iso_pred)
        vote_count += iso_pred

    reasons, suspicious_features, rule_risk_points = calculate_advanced_rules(features_dict)

    if total_models == 0:
        model_confidence = 0
    else:
        model_confidence = vote_count / total_models

    if rf_probability > 0:
        final_score = (model_confidence * 0.60) + (rf_probability * 0.40)
    else:
        final_score = model_confidence

    if rule_risk_points >= 8:
        final_score = max(final_score, 0.85)
    elif rule_risk_points >= 5:
        final_score = max(final_score, 0.75)
    elif rule_risk_points >= 3:
        final_score = max(final_score, 0.62)

    final_score = float(np.clip(final_score, 0, 1))

    is_anomaly = bool(final_score >= 0.60)

    confidence_percent = round(final_score * 100, 2)
    anomaly_score = confidence_percent
    severity_score = round((rule_risk_points / 15) * 100, 2)
    severity_score = float(np.clip(severity_score, 0, 100))

    if is_anomaly:
        prediction_label = "Suspicious Consumption Pattern"
        anomaly_type = classify_anomaly_type(features_dict)
    else:
        prediction_label = "Normal Consumption Pattern"
        anomaly_type = "Normal"

    risk_level = get_risk_level(confidence_percent, is_anomaly)
    inspection_priority = get_inspection_priority(risk_level)

    recommended_action = get_recommended_action(
        is_anomaly,
        anomaly_type,
        confidence_percent,
        risk_level
    )

    return {
        "is_anomaly": is_anomaly,
        "prediction_label": prediction_label,
        "confidence": confidence_percent,
        "confidence_percent": confidence_percent,
        "anomaly_score": anomaly_score,
        "severity_score": severity_score,
        "risk_level": risk_level,
        "inspection_priority": inspection_priority,
        "anomaly_type": anomaly_type,
        "cluster": cluster,
        "distance_to_center": round(distance_to_center, 4),
        "threshold": float(threshold),
        "models": model_votes,
        "voting": f"{vote_count}/{total_models} models flagged this household as suspicious.",
        "rf_probability": round(rf_probability * 100, 2),
        "rule_risk_points": rule_risk_points,
        "reasons": reasons,
        "suspicious_features": suspicious_features,
        "recommended_action": recommended_action,
        "feature_summary": {
            "total_daily": round(features_dict.get("total_daily", 0), 3),
            "avg_consumption": round(features_dict.get("avg_consumption", 0), 3),
            "max_consumption": round(features_dict.get("max_consumption", 0), 3),
            "min_consumption": round(features_dict.get("min_consumption", 0), 3),
            "night_ratio": round(features_dict.get("night_ratio", 0), 3),
            "zero_proportion": round(features_dict.get("zero_proportion", 0), 3),
            "load_factor": round(features_dict.get("load_factor", 0), 3),
            "cv": round(features_dict.get("cv", 0), 3),
            "peak_hour": round(features_dict.get("peak_hour", 0), 2)
        }
    }