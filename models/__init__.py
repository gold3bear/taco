"""
models/ — TACO Statement-Driven Data Models

Core domain models for the statement-driven TACO architecture.
"""

from models.statement import (
    Statement,
    StatementType,
    RhetoricIntensity,
    StatementStatus,
    InitialReaction,
    ReversalInfo,
    BASE_REVERSAL_RATES,
    TYPE_ASSET_MAP,
)

from models.five_factor import (
    FiveFactorModel,
    FiveFactorResult,
    FactorResult,
    calculate_reversal_probability,
)

from models.position_calculator import (
    TwoPhasePositionCalculator,
    TwoPhaseResult,
    TradeRecommendation,
    calculate_two_phase_position,
)

__all__ = [
    # Statement model
    "Statement",
    "StatementType",
    "RhetoricIntensity",
    "StatementStatus",
    "InitialReaction",
    "ReversalInfo",
    "BASE_REVERSAL_RATES",
    "TYPE_ASSET_MAP",
    # Five-Factor model
    "FiveFactorModel",
    "FiveFactorResult",
    "FactorResult",
    "calculate_reversal_probability",
    # Position calculator
    "TwoPhasePositionCalculator",
    "TwoPhaseResult",
    "TradeRecommendation",
    "calculate_two_phase_position",
]
