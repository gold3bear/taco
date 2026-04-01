"""
models/statement.py — Statement Data Model for TACO System

Core domain model for the statement-driven TACO architecture.
Each Trump statement is parsed into this structure for analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class StatementType(Enum):
    """Statement types ordered by historical reversal probability."""
    TRADE_TARIFF = "trade_tariff"       # Base reversal rate: 82%
    PERSONNEL = "personnel"             # Fed Chair, appointments — 78%
    TERRITORIAL = "territorial"         # Greenland, Panama, Canada — 58%
    MILITARY = "military"               # Iran, Afghanistan — 38%
    POLICY = "policy"                   # Fed, immigration — 15%
    SANCTIONS = "sanctions"            # Economic sanctions — 55%
    DIPLOMATIC = "diplomatic"          # Diplomatic relations — 60%


class RhetoricIntensity(Enum):
    """Intensity levels based on Trump statement language."""
    SOFT = "soft"     # "considering", "might", "exploring"
    MEDIUM = "medium" # "if you don't", "unless", "conditional"
    HARD = "hard"     # "will", "must", deadline specified
    EXTREME = "extreme"  # "all options on table", "existential"


class StatementStatus(Enum):
    """Lifecycle status of a statement."""
    ACTIVE = "active"      # Threat currently in effect
    REVERSED = "reversed"  # Trump backed down
    EXECUTED = "executed"  # Threat was carried out
    EXPIRED = "expired"    # Deadline passed without action
    AMBIGUOUS = "ambiguous"  # Partial reversal, mixed signals


# Historical base reversal rates by type
BASE_REVERSAL_RATES = {
    StatementType.TRADE_TARIFF: 0.82,
    StatementType.PERSONNEL: 0.78,
    StatementType.TERRITORIAL: 0.58,
    StatementType.MILITARY: 0.38,
    StatementType.POLICY: 0.15,
    StatementType.SANCTIONS: 0.55,
    StatementType.DIPLOMATIC: 0.60,
}

# Target assets by statement type
TYPE_ASSET_MAP = {
    StatementType.TRADE_TARIFF: ["SPY", "QQQ", "XRT", "DBA"],
    StatementType.MILITARY: ["SPY", "QQQ", "USO", "XLE", "GLD"],
    StatementType.TERRITORIAL: ["SPY", "EFA", "EEM"],
    StatementType.PERSONNEL: ["SPY", "XLB", "XLF"],
    StatementType.POLICY: ["TLT", "DXY", "SPY"],
    StatementType.SANCTIONS: ["USO", "XLE"],
    StatementType.DIPLOMATIC: ["EEM", "EFA", "SPY"],
}


@dataclass
class InitialReaction:
    """Market reaction data on threat day."""
    sp500_return: Optional[float] = None  # percent
    nasdaq_return: Optional[float] = None
    oil_return: Optional[float] = None
    btc_return: Optional[float] = None
    vix_change: Optional[float] = None   # percent
    bond_yield_change: Optional[float] = None


@dataclass
class ReversalInfo:
    """Information about reversal/backdown."""
    reversal_date: Optional[datetime] = None
    reversal_type: Optional[str] = None  # "explicit_walkback", "90-day_pause", "negotiated_deal", etc.
    reversal_trigger: Optional[str] = None
    days_to_reversal: Optional[int] = None
    rebound_magnitude: Optional[float] = None  # percent


@dataclass
class Statement:
    """
    Core domain model for a Trump statement.

    Represents a single geopolitical/economic threat or声明
    with classification, market predictions, and outcome tracking.
    """
    # Identification
    id: str  # UUID or TACO-XXX format

    # Content
    raw_text: str                    # Full statement text
    source: str                      # truth_social, press_conf, tweet, interview, news_report
    published_at: datetime

    # Classification
    statement_type: StatementType
    rhetoric_intensity: RhetoricIntensity
    target_entity: str              # Country, organization, or sector targeted
    target_assets: list[str]         # Affected tickers/sectors

    # Temporal
    has_deadline: bool
    deadline_date: Optional[datetime] = None

    # Desensitization tracking
    nth_similar_threat: int = 1     # Count of similar threats in sequence

    # Outcome
    status: StatementStatus = StatementStatus.ACTIVE

    # Market data
    initial_reaction: Optional[InitialReaction] = None
    reversal_info: Optional[ReversalInfo] = None

    # Analysis results (populated after running analysis)
    predicted_reversal_prob: Optional[float] = None
    predicted_initial_return: Optional[float] = None
    desensitized_return: Optional[float] = None
    five_factor_breakdown: Optional[dict] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0

    def __post_init__(self):
        """Derive target_assets from type if not provided."""
        if not self.target_assets and self.statement_type:
            self.target_assets = TYPE_ASSET_MAP.get(self.statement_type, ["SPY"])

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "raw_text": self.raw_text,
            "source": self.source,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "statement_type": self.statement_type.value if self.statement_type else None,
            "rhetoric_intensity": self.rhetoric_intensity.value if self.rhetoric_intensity else None,
            "target_entity": self.target_entity,
            "target_assets": self.target_assets,
            "has_deadline": self.has_deadline,
            "deadline_date": self.deadline_date.isoformat() if self.deadline_date else None,
            "nth_similar_threat": self.nth_similar_threat,
            "status": self.status.value if self.status else None,
            "initial_reaction": {
                "sp500_return": self.initial_reaction.sp500_return if self.initial_reaction else None,
                "nasdaq_return": self.initial_reaction.nasdaq_return if self.initial_reaction else None,
                "oil_return": self.initial_reaction.oil_return if self.initial_reaction else None,
                "btc_return": self.initial_reaction.btc_return if self.initial_reaction else None,
                "vix_change": self.initial_reaction.vix_change if self.initial_reaction else None,
            } if self.initial_reaction else None,
            "reversal_info": {
                "reversal_date": self.reversal_info.reversal_date.isoformat() if self.reversal_info and self.reversal_info.reversal_date else None,
                "reversal_type": self.reversal_info.reversal_type if self.reversal_info else None,
                "days_to_reversal": self.reversal_info.days_to_reversal if self.reversal_info else None,
                "rebound_magnitude": self.reversal_info.rebound_magnitude if self.reversal_info else None,
            } if self.reversal_info else None,
            "predicted_reversal_prob": self.predicted_reversal_prob,
            "predicted_initial_return": self.predicted_initial_return,
            "desensitized_return": self.desensitized_return,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Statement":
        """Deserialize from dictionary."""
        from datetime import datetime as dt

        # Parse nested objects
        initial_reaction = None
        if data.get("initial_reaction"):
            ir_data = data["initial_reaction"]
            initial_reaction = InitialReaction(
                sp500_return=ir_data.get("sp500_return"),
                nasdaq_return=ir_data.get("nasdaq_return"),
                oil_return=ir_data.get("oil_return"),
                btc_return=ir_data.get("btc_return"),
                vix_change=ir_data.get("vix_change"),
            )

        reversal_info = None
        if data.get("reversal_info"):
            ri_data = data["reversal_info"]
            reversal_info = ReversalInfo(
                reversal_date=dt.fromisoformat(ri_data["reversal_date"]) if ri_data.get("reversal_date") else None,
                reversal_type=ri_data.get("reversal_type"),
                reversal_trigger=ri_data.get("reversal_trigger"),
                days_to_reversal=ri_data.get("days_to_reversal"),
                rebound_magnitude=ri_data.get("rebound_magnitude"),
            )

        return cls(
            id=data["id"],
            raw_text=data["raw_text"],
            source=data["source"],
            published_at=dt.fromisoformat(data["published_at"]) if data.get("published_at") else None,
            statement_type=StatementType(data["statement_type"]) if data.get("statement_type") else None,
            rhetoric_intensity=RhetoricIntensity(data["rhetoric_intensity"]) if data.get("rhetoric_intensity") else None,
            target_entity=data.get("target_entity", ""),
            target_assets=data.get("target_assets", []),
            has_deadline=data.get("has_deadline", False),
            deadline_date=dt.fromisoformat(data["deadline_date"]) if data.get("deadline_date") else None,
            nth_similar_threat=data.get("nth_similar_threat", 1),
            status=StatementStatus(data["status"]) if data.get("status") else StatementStatus.ACTIVE,
            initial_reaction=initial_reaction,
            reversal_info=reversal_info,
            predicted_reversal_prob=data.get("predicted_reversal_prob"),
            predicted_initial_return=data.get("predicted_initial_return"),
            desensitized_return=data.get("desensitized_return"),
            confidence=data.get("confidence", 1.0),
        )
