from enum import StrEnum


class PredictionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class ExplanationType(StrEnum):
    FEATURE_CONTRIBUTION = "feature_contribution"
    FEATURE_IMPORTANCE = "feature_importance"


class GovernanceDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
