from datetime import date
from decimal import Decimal
import math
import numpy as np
import pandas as pd


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth in kilometers."""
    R = 6371.0088  # Earth mean radius in kilometers
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

# Red blood cell compatibility dictionary
ABO_RH_COMPATIBILITY = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],  # Universal recipient
}

URGENCY_MAP = {
    "routine": 1.0,
    "urgent": 2.0,
    "critical_stat": 3.0,
}

FEATURE_COLUMNS = [
    "abo_compatible",
    "distance_km",
    "days_since_last_donation",
    "donation_count",
    "hemoglobin_level",
    "bp_score",
    "urgency_weight",
    "donor_age",
]


def is_blood_compatible(donor_group: str, recipient_group: str) -> bool:
    """Determine biological compatibility based on standard ABO/Rh antigens."""
    recipient_group = recipient_group.strip().upper()
    donor_group = donor_group.strip().upper()
    valid_donors = ABO_RH_COMPATIBILITY.get(recipient_group, [])
    return donor_group in valid_donors


def calculate_bp_score(systolic: int, diastolic: int) -> float:
    """Calculate normal blood pressure deviation score (1.0 = perfect 120/80)."""
    sys_dev = abs(float(systolic) - 120.0) / 120.0
    dia_dev = abs(float(diastolic) - 80.0) / 80.0
    return max(0.0, 1.0 - (sys_dev + dia_dev) / 2.0)


def extract_match_features(donor, hospital, urgency: str = "urgent") -> dict:
    """Extract clinical, geospatial, and logistical feature dict for ML scoring."""
    distance = haversine_distance_km(
        float(donor.latitude),
        float(donor.longitude),
        float(hospital.latitude),
        float(hospital.longitude),
    )

    if donor.last_donation_date:
        today = date.today()
        days_since = (today - donor.last_donation_date).days
    else:
        days_since = 365.0  # Eligible fresh donor

    bp_score = calculate_bp_score(donor.systolic_bp, donor.diastolic_bp)
    urgency_weight = URGENCY_MAP.get(urgency, 1.0)

    return {
        "abo_compatible": 1.0,  # Will be overridden by caller if recipient known
        "distance_km": float(distance),
        "days_since_last_donation": float(days_since),
        "donation_count": float(donor.donation_count),
        "hemoglobin_level": float(donor.hemoglobin_level),
        "bp_score": float(bp_score),
        "urgency_weight": float(urgency_weight),
        "donor_age": float(donor.age),
    }


def to_feature_vector(feature_dict: dict) -> pd.DataFrame:
    """Convert feature dict to ordered DataFrame with feature names for scikit-learn model."""
    vals = [feature_dict[col] for col in FEATURE_COLUMNS]
    return pd.DataFrame([vals], columns=FEATURE_COLUMNS)
