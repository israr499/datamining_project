

from statistics import mean



def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, value))




def calculate_trend(values):
    """
    Simple trend detector.
    Returns:
        Increasing
        Decreasing
        Stable
        Insufficient Data
    """

    if not values or len(values) < 3:
        return "Insufficient Data"

    first_half = values[:len(values) // 2]
    second_half = values[len(values) // 2:]

    first_avg = mean(first_half)
    second_avg = mean(second_half)

    difference = second_avg - first_avg

    if difference >= 5:
        return "Increasing"

    if difference <= -5:
        return "Decreasing"

    return "Stable"


def calculate_recent_anomaly_count(history, recent_limit=5):
    """
    Count suspicious detections in recent records.
    """

    if not history:
        return 0

    recent_records = history[:recent_limit]

    count = 0

    for row in recent_records:
        if safe_int(row.get("is_anomaly", 0)) == 1:
            count += 1

    return count


def calculate_average_zero_intervals(history):
    if not history:
        return 0.0

    values = [safe_float(row.get("zero_intervals", 0)) for row in history]

    return mean(values) if values else 0.0


def calculate_average_confidence(history):
    if not history:
        return 0.0

    values = [safe_float(row.get("confidence", 0)) for row in history]

    return mean(values) if values else 0.0


def calculate_suspicious_rate(history):
    if not history:
        return 0.0

    total = len(history)

    suspicious = 0

    for row in history:
        if safe_int(row.get("is_anomaly", 0)) == 1:
            suspicious += 1

    return (suspicious / total) * 100


def calculate_consumption_stability(history):
    """
    Measures whether total consumption is stable or unstable.
    Stable suspicious behavior can still be risky if zero intervals repeat.
    Returns low/medium/high instability percentage.
    """

    if not history or len(history) < 3:
        return 0.0

    values = [safe_float(row.get("total_consumption", 0)) for row in history]

    avg_value = mean(values)

    if avg_value == 0:
        return 0.0

    deviation = mean([abs(v - avg_value) for v in values])

    instability = (deviation / avg_value) * 100

    return clamp(instability, 0, 100)


# ============================================
# FORECAST LEVEL
# ============================================

def get_forecast_level(probability):
    probability = safe_float(probability)

    if probability >= 85:
        return "Very High Future Risk"

    if probability >= 70:
        return "High Future Risk"

    if probability >= 50:
        return "Moderate Future Risk"

    if probability >= 30:
        return "Low Future Risk"

    return "Very Low Future Risk"


def get_forecast_window(probability):
    probability = safe_float(probability)

    if probability >= 85:
        return "Next 1–3 Days"

    if probability >= 70:
        return "Next 3–7 Days"

    if probability >= 50:
        return "Next 7–14 Days"

    return "No urgent forecast window"


def get_recommended_action(probability, trend, suspicious_rate, avg_zero_intervals):
    probability = safe_float(probability)
    suspicious_rate = safe_float(suspicious_rate)
    avg_zero_intervals = safe_float(avg_zero_intervals)

    if probability >= 85:
        return "Immediate inspection recommended. Household shows very high future theft risk."

    if probability >= 70:
        return "Schedule field inspection and monitor readings closely in the next week."

    if probability >= 50:
        return "Monitor this household. Risk is moderate and may increase if suspicious behavior repeats."

    if suspicious_rate >= 50 or avg_zero_intervals >= 10:
        return "Continue monitoring because some suspicious indicators are present."

    return "No immediate action required. Continue normal monitoring."


def build_forecast_reason(
    probability,
    trend,
    suspicious_rate,
    avg_confidence,
    recent_anomaly_count,
    avg_zero_intervals,
    consumption_instability
):
    reasons = []

    if suspicious_rate >= 80:
        reasons.append("high repeated suspicious detection rate")

    elif suspicious_rate >= 50:
        reasons.append("moderate repeated suspicious detection rate")

    if avg_confidence >= 80:
        reasons.append("consistently high anomaly confidence")

    elif avg_confidence >= 60:
        reasons.append("moderate anomaly confidence")

    if recent_anomaly_count >= 4:
        reasons.append("multiple recent suspicious detections")

    elif recent_anomaly_count >= 2:
        reasons.append("some recent suspicious detections")

    if avg_zero_intervals >= 20:
        reasons.append("frequent extended zero-consumption intervals")

    elif avg_zero_intervals >= 10:
        reasons.append("noticeable zero-consumption intervals")

    if trend == "Increasing":
        reasons.append("risk trend is increasing")

    elif trend == "Decreasing":
        reasons.append("risk trend is decreasing")

    if consumption_instability >= 25:
        reasons.append("unstable total consumption pattern")

    if not reasons:
        reasons.append("household currently has limited future-risk indicators")

    return "Forecast generated based on " + ", ".join(reasons) + "."


# ============================================
# MAIN FORECAST FUNCTION
# ============================================

def forecast_household_future_risk(household_id, history):
    """
    Main function used by API later.

    Input:
        household_id: string
        history: list of detection rows from get_household_history()

    Output:
        dictionary forecast result
    """

    if not history:
        return {
            "success": False,
            "household_id": household_id,
            "message": "No historical detection data available for forecasting.",
            "future_risk_probability": 0.0,
            "forecast_level": "Insufficient Data",
            "forecast_window": "No forecast available",
            "risk_trend": "Insufficient Data",
            "forecast_reason": "No stored history exists for this household.",
            "recommended_action": "Run predictions first to generate household history.",
            "forecast_points": []
        }

    # History usually comes latest-first from DB.
    # Reverse it to oldest-first for trend calculation.
    chronological_history = list(reversed(history))

    confidence_values = [
        safe_float(row.get("confidence", 0))
        for row in chronological_history
    ]

    anomaly_flags = [
        safe_int(row.get("is_anomaly", 0))
        for row in chronological_history
    ]

    zero_values = [
        safe_float(row.get("zero_intervals", 0))
        for row in chronological_history
    ]

    total_values = [
        safe_float(row.get("total_consumption", 0))
        for row in chronological_history
    ]

    risk_trend = calculate_trend(confidence_values)

    suspicious_rate = calculate_suspicious_rate(history)
    avg_confidence = calculate_average_confidence(history)
    avg_zero_intervals = calculate_average_zero_intervals(history)
    recent_anomaly_count = calculate_recent_anomaly_count(history, recent_limit=5)
    consumption_instability = calculate_consumption_stability(history)

    latest = history[0]
    latest_confidence = safe_float(latest.get("confidence", 0))
    latest_is_anomaly = safe_int(latest.get("is_anomaly", 0))
    latest_zero_intervals = safe_float(latest.get("zero_intervals", 0))

    # Weighted forecast score
    score = 0.0

    # Repeated suspicious behavior
    score += suspicious_rate * 0.30

    # Average confidence
    score += avg_confidence * 0.25

    # Latest confidence
    score += latest_confidence * 0.20

    # Recent suspicious count out of 5
    score += (recent_anomaly_count / 5) * 100 * 0.10

    # Zero interval behavior
    zero_score = clamp((avg_zero_intervals / 30) * 100, 0, 100)
    score += zero_score * 0.10

    # Instability
    instability_score = clamp(consumption_instability, 0, 100)
    score += instability_score * 0.05

    # Trend adjustment
    if risk_trend == "Increasing":
        score += 8

    elif risk_trend == "Decreasing":
        score -= 8

    # Latest anomaly bonus
    if latest_is_anomaly == 1:
        score += 5

    # Very high latest zero interval bonus
    if latest_zero_intervals >= 20:
        score += 5

    future_risk_probability = clamp(score, 0, 100)

    forecast_level = get_forecast_level(future_risk_probability)
    forecast_window = get_forecast_window(future_risk_probability)

    forecast_reason = build_forecast_reason(
        probability=future_risk_probability,
        trend=risk_trend,
        suspicious_rate=suspicious_rate,
        avg_confidence=avg_confidence,
        recent_anomaly_count=recent_anomaly_count,
        avg_zero_intervals=avg_zero_intervals,
        consumption_instability=consumption_instability
    )

    recommended_action = get_recommended_action(
        probability=future_risk_probability,
        trend=risk_trend,
        suspicious_rate=suspicious_rate,
        avg_zero_intervals=avg_zero_intervals
    )

    forecast_points = build_forecast_points(
        confidence_values=confidence_values,
        future_risk_probability=future_risk_probability
    )

    return {
        "success": True,
        "household_id": household_id,
        "future_risk_probability": round(future_risk_probability, 2),
        "forecast_level": forecast_level,
        "forecast_window": forecast_window,
        "risk_trend": risk_trend,
        "suspicious_rate": round(suspicious_rate, 2),
        "avg_confidence": round(avg_confidence, 2),
        "recent_anomaly_count": recent_anomaly_count,
        "avg_zero_intervals": round(avg_zero_intervals, 2),
        "consumption_instability": round(consumption_instability, 2),
        "forecast_reason": forecast_reason,
        "recommended_action": recommended_action,
        "forecast_points": forecast_points,
        "debug_inputs": {
            "confidence_values": confidence_values,
            "anomaly_flags": anomaly_flags,
            "zero_values": zero_values,
            "total_values": total_values
        }
    }


# ============================================
# FORECAST CHART POINTS
# ============================================

def build_forecast_points(confidence_values, future_risk_probability):
    """
    Creates simple projection points for chart visualization.
    """

    if not confidence_values:
        return []

    last_confidence = confidence_values[-1]

    future_risk_probability = safe_float(future_risk_probability)

    p1 = last_confidence + ((future_risk_probability - last_confidence) * 0.33)
    p2 = last_confidence + ((future_risk_probability - last_confidence) * 0.66)
    p3 = future_risk_probability

    return [
        {
            "label": "Current",
            "value": round(last_confidence, 2)
        },
        {
            "label": "+1 Day",
            "value": round(clamp(p1), 2)
        },
        {
            "label": "+3 Days",
            "value": round(clamp(p2), 2)
        },
        {
            "label": "+7 Days",
            "value": round(clamp(p3), 2)
        }
    ]


# ============================================
# QUICK LOCAL TEST
# ============================================

if __name__ == "__main__":
    sample_history = [
        {
            "household_id": "THEFT_NIG_01",
            "is_anomaly": 1,
            "confidence": 85,
            "zero_intervals": 28,
            "total_consumption": 51.91
        },
        {
            "household_id": "THEFT_NIG_01",
            "is_anomaly": 1,
            "confidence": 85,
            "zero_intervals": 28,
            "total_consumption": 51.91
        },
        {
            "household_id": "THEFT_NIG_01",
            "is_anomaly": 1,
            "confidence": 75,
            "zero_intervals": 28,
            "total_consumption": 51.91
        },
        {
            "household_id": "THEFT_NIG_01",
            "is_anomaly": 1,
            "confidence": 75,
            "zero_intervals": 28,
            "total_consumption": 51.91
        }
    ]

    result = forecast_household_future_risk("THEFT_NIG_01", sample_history)

    print("\nForecast Test Result:")
    print("=" * 50)

    for key, value in result.items():
        print(f"{key}: {value}")