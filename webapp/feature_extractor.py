

import numpy as np
from datetime import datetime


def extract_features_from_raw(consumption_data):
    """
    Extract features from one household's 24-hour electricity consumption pattern.

    Input:
        consumption_data = 96 readings
        96 readings means 24 hours × 4 readings per hour

    Output:
        Dictionary of features used by trained ML models.
    """

    consumption = np.array(consumption_data, dtype=float)

    if len(consumption) != 96:
        raise ValueError(
            f"Expected 96 readings for one day, but got {len(consumption)} readings."
        )

    # Remove negative values if any
    consumption = np.where(consumption < 0, 0, consumption)

    features = {}


    total_daily = np.sum(consumption)
    avg_consumption = np.mean(consumption)
    std_consumption = np.std(consumption)
    min_consumption = np.min(consumption)
    max_consumption = np.max(consumption)
    median_consumption = np.median(consumption)

    features["total_daily"] = float(total_daily)
    features["avg_consumption"] = float(avg_consumption)
    features["std_consumption"] = float(std_consumption)
    features["min_consumption"] = float(min_consumption)
    features["max_consumption"] = float(max_consumption)
    features["median_consumption"] = float(median_consumption)
    features["consumption_range"] = float(max_consumption - min_consumption)
    features["cv"] = float(std_consumption / (avg_consumption + 1e-6))

    # ============================================
    # Time based features
    # ============================================
    # 96 intervals, 4 intervals per hour
    # 6 AM - 9 AM
    morning_idx = list(range(24, 36))

    # 5 PM - 8 PM
    evening_idx = list(range(68, 80))

    # 11 PM - 5 AM
    night_idx = list(range(0, 20)) + list(range(92, 96))

    morning_values = consumption[morning_idx]
    evening_values = consumption[evening_idx]
    night_values = consumption[night_idx]

    features["morning_peak"] = float(np.max(morning_values))
    features["evening_peak"] = float(np.max(evening_values))
    features["night_consumption"] = float(np.mean(night_values))
    features["night_ratio"] = float(features["night_consumption"] / (avg_consumption + 1e-6))

    # ============================================
    # Zero / low usage features
    # ============================================
    zero_intervals = np.sum(consumption < 0.1)

    features["zero_intervals"] = int(zero_intervals)
    features["zero_proportion"] = float(zero_intervals / 96)

    # ============================================
    # Peak features
    # ============================================
    peak_idx = int(np.argmax(consumption))
    features["peak_hour"] = float(peak_idx / 4)

    # ============================================
    # Ramp features
    # ============================================
    morning_ramp_idx = list(range(20, 36))   # 5 AM - 9 AM
    evening_ramp_idx = list(range(64, 84))   # 4 PM - 9 PM

    features["morning_ramp"] = float(
        np.max(consumption[morning_ramp_idx]) - np.min(consumption[morning_ramp_idx])
    )

    features["evening_ramp"] = float(
        np.max(consumption[evening_ramp_idx]) - np.min(consumption[evening_ramp_idx])
    )

    # ============================================
    # Load factor
    # ============================================
    features["load_factor"] = float(avg_consumption / (max_consumption + 1e-6))

    # ============================================
    # Rolling features
    # For web prediction, we only have one day.
    # So these are estimated from the same daily pattern.
    # ============================================
    features["rolling_7day_mean"] = float(avg_consumption)
    features["rolling_7day_std"] = float(std_consumption)
    features["rolling_7day_max"] = float(max_consumption)
    features["zscore_7day"] = 0.0

    # ============================================
    # Date/time features
    # ============================================
    now = datetime.now()
    day_of_week = now.weekday()

    features["day_of_week"] = int(day_of_week)
    features["is_weekend"] = int(day_of_week >= 5)
    features["is_monday"] = int(day_of_week == 0)
    features["is_friday"] = int(day_of_week == 4)
    features["month"] = int(now.month)

    if now.month in [12, 1, 2]:
        season = 0      # Winter
    elif now.month in [3, 4, 5]:
        season = 1      # Spring
    elif now.month in [6, 7, 8]:
        season = 2      # Summer
    else:
        season = 3      # Fall

    features["season"] = int(season)

    return features


def generate_sample_pattern(pattern_type="normal"):
    """
    Generate sample 24-hour electricity patterns for testing.

    pattern_type:
        normal
        peak_clipping
        night_zeroing
        overall_reduction
        spike
    """

    consumption = []

    for hour in range(24):
        for _ in range(4):

            if 6 <= hour < 9:
                value = np.random.uniform(0.8, 1.5)

            elif 17 <= hour < 20:
                value = np.random.uniform(1.0, 2.0)

            elif hour >= 23 or hour < 5:
                value = np.random.uniform(0.05, 0.30)

            else:
                value = np.random.uniform(0.30, 0.70)

            consumption.append(value)

    consumption = np.array(consumption)

    if pattern_type == "peak_clipping":
        consumption = np.minimum(consumption, 0.8)

    elif pattern_type == "night_zeroing":
        night_indices = list(range(0, 20)) + list(range(92, 96))
        consumption[night_indices] = 0

    elif pattern_type == "overall_reduction":
        consumption = consumption * 0.45

    elif pattern_type == "spike":
        spike_indices = np.random.choice(96, 5, replace=False)
        consumption[spike_indices] = consumption[spike_indices] * 3.5

    return consumption.round(3).tolist()