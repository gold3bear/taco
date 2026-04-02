"""
models/congress_output_schema.py — Congressional Speech Analysis Output Schema

标准输出 Schema，确保 JSON 和 Markdown 使用相同数据结构。

Schema Version: 1.0
"""

from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime


@dataclass
class MarketData:
    vix: dict
    wti_crude: dict
    spy: dict
    gld: dict
    polymarket_backdown: float


@dataclass
class CredibilityClaim:
    score: int
    source: str
    notes: Optional[str] = None


@dataclass
class CredibilityAssessment:
    weighted_average: int
    note: str
    claims: dict


@dataclass
class ExpectedValue:
    ev_pct: float
    calculation: str
    recommendation: Optional[str] = None


@dataclass
class InvestmentRecommendation:
    asset: str
    direction: str
    size_pct: int
    rationale: str


@dataclass
class ScenarioProbabilities:
    A_fast_resolution: float
    B_stalemate: float
    C_escalation_direct: float
    C_with_hormuz: float


@dataclass
class TACOReversalAssessment:
    is_taco_event: bool
    reversal_probability: float
    polymarket_backdown_prob: float
    reasoning: str


@dataclass
class AgentOutput:
    escalation_ratio: Optional[float] = None
    tone_delta: Optional[str] = None
    face_saving_mention: Optional[bool] = None
    exit_mechanism_present: Optional[bool] = None
    confidence: Optional[int] = None
    weighted_credibility: Optional[int] = None
    most_damaging_attack: Optional[str] = None
    pattern_match_score: Optional[int] = None


@dataclass
class KeyContradiction:
    issue: str
    polymarket_value: Optional[float] = None
    model_value: Optional[float] = None
    divergence_bp: Optional[int] = None
    severity: str = ""


@dataclass
class TailRisk:
    risk: str
    probability_add_pct: Optional[float] = None
    probability: Optional[str] = None
    impact: str


@dataclass
class MonitoringTrigger:
    trigger: str


@dataclass
class CongressSpeechOutput:
    """Congressional Speech Analysis Output Schema"""
    version: str = "1.0"
    speech_id: str = ""
    analysis_timestamp: str = ""
    confidence_score: int = 0
    confidence_note: str = ""

    scenario_probabilities: Optional[ScenarioProbabilities] = None
    taco_reversal_assessment: Optional[TACOReversalAssessment] = None

    market_data: Optional[MarketData] = None
    credibility_assessment: Optional[CredibilityAssessment] = None

    expected_values: Optional[dict] = None
    investment_recommendations: Optional[List[InvestmentRecommendation]] = None

    agent_outputs: Optional[dict] = None
    key_contradictions: Optional[List[KeyContradiction]] = None
    tail_risks: Optional[List[TailRisk]] = None
    monitoring_triggers: Optional[List[MonitoringTrigger]] = None

    data_sources: Optional[List[str]] = None
    output_files: Optional[dict] = None

    def to_dict(self) -> dict:
        """转换为字典，用于 JSON 序列化"""
        d = asdict(self)
        d['version'] = self.version
        return d

    @classmethod
    def from_dict(cls, data: dict) -> 'CongressSpeechOutput':
        """从字典创建对象"""
        return cls(**data)

    def validate(self) -> List[str]:
        """验证输出完整性，返回错误列表"""
        errors = []

        if not self.speech_id:
            errors.append("speech_id is required")
        if not self.analysis_timestamp:
            errors.append("analysis_timestamp is required")
        if not (0 <= self.confidence_score <= 100):
            errors.append("confidence_score must be 0-100")

        if self.scenario_probabilities:
            sp = self.scenario_probabilities
            total = sp.A_fast_resolution + sp.B_stalemate + sp.C_escalation_direct
            if abs(total - 1.0) > 0.01:
                errors.append(f"scenario probabilities sum to {total}, expected 1.0")

        if self.investment_recommendations:
            total_size = sum(r.size_pct for r in self.investment_recommendations)
            if total_size > 100:
                errors.append(f"total position size {total_size}% exceeds 100%")

        return errors


# 便捷函数
def create_minimal_output(
    speech_id: str,
    confidence_score: int,
    scenario_probs: dict,
    investment_recs: list
) -> CongressSpeechOutput:
    """创建最小化的输出对象"""
    return CongressSpeechOutput(
        speech_id=speech_id,
        analysis_timestamp=datetime.now().isoformat(),
        confidence_score=confidence_score,
        scenario_probabilities=ScenarioProbabilities(**scenario_probs),
        investment_recommendations=[InvestmentRecommendation(**r) for r in investment_recs]
    )
