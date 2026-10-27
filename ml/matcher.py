import logging
from pathlib import Path
import joblib
import numpy as np
from django.conf import settings
from ml.features import (
    extract_match_features,
    is_blood_compatible,
    to_feature_vector,
)

logger = logging.getLogger(__name__)


class CompatibilityMatcher:
    """Production ML inference engine scoring donor-recipient compatibility and match probability."""

    _instance = None
    _model = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.model_path = getattr(
            settings,
            "ML_MODEL_PATH",
            Path(__file__).resolve().parent / "models" / "compatibility_rf.joblib",
        )
        self.model = self._load_model()

    def _load_model(self):
        if Path(self.model_path).exists():
            try:
                model = joblib.load(self.model_path)
                logger.info("Loaded Random Forest model from %s", self.model_path)
                return model
            except Exception as exc:
                logger.warning("Failed to load model file %s: %s", self.model_path, exc)
        return None

    def score_donor(
        self,
        donor,
        hospital,
        recipient_blood_group: str,
        urgency: str = "urgent",
    ) -> dict:
        """Calculate match probability (0.0 to 1.0) and clinical breakdown for a donor candidate."""
        # 1. Biological ABO/Rh compatibility rule check
        compatible = is_blood_compatible(donor.blood_group, recipient_blood_group)
        if not compatible or not donor.is_eligible:
            return {
                "score": 0.0,
                "is_compatible": compatible,
                "is_eligible": donor.is_eligible,
                "distance_km": 0.0,
                "tier": "incompatible",
            }

        # 2. Extract feature vector
        features = extract_match_features(donor, hospital, urgency=urgency)
        features["abo_compatible"] = 1.0 if compatible else 0.0

        score = 0.5  # Heuristic default fallback

        if self.model is not None:
            try:
                vec = to_feature_vector(features)
                probs = self.model.predict_proba(vec)[0]
                # Index 1 is probability of successful match
                score = float(probs[1]) if len(probs) > 1 else float(probs[0])
            except Exception as exc:
                logger.warning("ML inference fallback on error: %s", exc)
                score = self._fallback_score(features)
        else:
            score = self._fallback_score(features)

        # Scale score to percentage [0.0, 1.0]
        score = max(0.01, min(0.99, score))

        tier = "high" if score >= 0.75 else "moderate" if score >= 0.50 else "low"

        return {
            "score": round(score, 3),
            "is_compatible": True,
            "is_eligible": donor.is_eligible,
            "distance_km": round(features["distance_km"], 2),
            "tier": tier,
            "clinical_features": features,
        }

    def _fallback_score(self, features: dict) -> float:
        """Deterministic heuristic fallback if model weights are unavailable."""
        dist = features["distance_km"]
        days = features["days_since_last_donation"]
        bp = features["bp_score"]
        hb = features["hemoglobin_level"]

        score = 0.4
        if dist <= 15.0:
            score += 0.25
        elif dist <= 30.0:
            score += 0.15

        if days >= 56:
            score += 0.15

        if hb >= 12.5:
            score += 0.10

        score += bp * 0.10
        return score

    def rank_donors(
        self,
        donors,
        hospital,
        recipient_blood_group: str,
        urgency: str = "urgent",
    ) -> list:
        """Score and sort a queryset or list of donors in descending order of match quality."""
        ranked = []
        for donor in donors:
            eval_res = self.score_donor(donor, hospital, recipient_blood_group, urgency=urgency)
            if eval_res["is_compatible"] and eval_res["score"] > 0:
                ranked.append(
                    {
                        "donor": donor,
                        "match_score": eval_res["score"],
                        "distance_km": eval_res["distance_km"],
                        "tier": eval_res["tier"],
                        "eval_details": eval_res,
                    }
                )

        ranked.sort(key=lambda x: x["match_score"], reverse=True)
        return ranked
