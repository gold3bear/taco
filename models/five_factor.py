"""
models/five_factor.py — Five-Factor Reversal Probability Model

Calculates reversal probability for Trump statements using 5 factors:
- Factor 1: Base rate by statement type (TRADE 82%, MILITARY 38%, etc.)
- Factor 2: Market pain degree (VIX level)
- Factor 3: Counterparty concession signals
- Factor 4: Domestic political pressure
- Factor 5: Polymarket calibration (5% weight)
"""

from dataclasses import dataclass
from typing import Optional

from models.statement import StatementType, BASE_REVERSAL_RATES


@dataclass
class FactorResult:
    """Result of a single factor calculation."""
    name: str
    value: float
    weight: Optional[float] = None
    details: Optional[dict] = None


@dataclass
class FiveFactorResult:
    """Complete Five-Factor Model output."""
    probability: float
    confidence: float
    factor_1: FactorResult
    factor_2: FactorResult
    factor_3: FactorResult
    factor_4: FactorResult
    factor_5: FactorResult
    desensitization_multiplier: float = 1.0
    desensitized_return: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "probability": self.probability,
            "confidence": self.confidence,
            "factors": {
                "factor_1_base_rate": {
                    "name": self.factor_1.name,
                    "value": self.factor_1.value,
                    "details": self.factor_1.details,
                },
                "factor_2_market_pain": {
                    "name": self.factor_2.name,
                    "value": self.factor_2.value,
                    "weight": self.factor_2.weight,
                    "details": self.factor_2.details,
                },
                "factor_3_counterparty": {
                    "name": self.factor_3.name,
                    "value": self.factor_3.value,
                    "details": self.factor_3.details,
                },
                "factor_4_domestic": {
                    "name": self.factor_4.name,
                    "value": self.factor_4.value,
                    "details": self.factor_4.details,
                },
                "factor_5_polymarket": {
                    "name": self.factor_5.name,
                    "value": self.factor_5.value,
                    "weight": self.factor_5.weight,
                    "details": self.factor_5.details,
                },
            },
            "desensitization": {
                "multiplier": self.desensitization_multiplier,
                "desensitized_return": self.desensitized_return,
            }
        }


class FiveFactorModel:
    """
    Five-Factor Reversal Probability Model for Trump statements.

    Formula:
    P(reversal) = Factor1 × (1 + 0.25×Factor2) × (1 + Factor3) × (1 + Factor4) × (1 + 0.05×Factor5)

    Where:
    - Factor1: Base rate by statement type (0.15 to 0.82)
    - Factor2: Market pain multiplier (0.1 to 1.0), weight 25%
    - Factor3: Counterparty adjustment (-0.30 to +0.30)
    - Factor4: Domestic pressure adjustment (0 to +0.15)
    - Factor5: Polymarket calibration adjustment (-0.10 to +0.10), weight 5%
    """

    # Factor 2: Market pain thresholds
    VIX_THRESHOLDS = [
        (20, 1.0),   # VIX > 20: maximum pain
        (10, 0.7),   # VIX 10-20: high pain
        (5, 0.4),    # VIX 5-10: moderate pain
        (0, 0.1),    # VIX < 5: low pain
    ]

    # Factor 3: Counterparty signals
    COUNTERPARTY_SIGNALS = {
        "symbolic_concession": +0.20,
        "counter_offer": +0.10,
        "third_party_mediator": +0.15,
        "back_channel_confirmed": +0.10,
        "neutral": 0.0,
        "no_response": 0.0,
        "hard_rejection": -0.25,
        "survival_stakes": -0.30,
        "leadership_vacuum": -0.20,
    }

    # Factor 4: Domestic pressure
    DOMESTIC_TRIGGERS = {
        "gas_above_4": +0.08,
        "midterm_within_6m": +0.06,
        "approval_drop_3pp": +0.05,
        "market_down_5pct": +0.07,
        "ally_backlash": +0.04,
    }

    # Desensitization: each similar threat reduces market impact by 15%
    DESENSITIZATION_BASE = 0.85

    def calculate(
        self,
        statement_type: StatementType,
        vix_current: float,
        counterparty_signal: str = "neutral",
        gas_price: float = 3.50,
        midterm_months: int = 12,
        market_drawdown: float = 0.0,
        polymarket_prob: Optional[float] = None,
        nth_similar_threat: int = 1,
        base_return: Optional[float] = None,
    ) -> FiveFactorResult:
        """
        Calculate reversal probability using Five-Factor Model.

        Args:
            statement_type: Type of statement (TRADE_TARIFF, MILITARY, etc.)
            vix_current: Current VIX level
            counterparty_signal: Signal from counterparty (symbolic_concession, hard_rejection, etc.)
            gas_price: Current gas price in $/gallon
            midterm_months: Months until next midterm election
            market_drawdown: Market drawdown from recent peak in percent
            polymarket_prob: Polymarket reversal probability (0-1)
            nth_similar_threat: Number of similar threats in sequence (for desensitization)
            base_return: Base predicted return for desensitization calculation

        Returns:
            FiveFactorResult with probability and factor breakdown
        """
        # Factor 1: Base rate by type
        base_rate = BASE_REVERSAL_RATES.get(statement_type, 0.50)
        f1 = FactorResult(
            name="base_rate",
            value=base_rate,
            details={"statement_type": statement_type.value}
        )

        # Factor 2: Market pain
        f2_value = self._factor_2_market_pain(vix_current)
        f2 = FactorResult(
            name="market_pain",
            value=f2_value,
            weight=0.25,
            details={"vix_current": vix_current}
        )

        # Factor 3: Counterparty signals
        f3_value = self.COUNTERPARTY_SIGNALS.get(counterparty_signal, 0.0)
        f3 = FactorResult(
            name="counterparty",
            value=f3_value,
            details={"signal": counterparty_signal}
        )

        # Factor 4: Domestic pressure
        f4_value = self._factor_4_domestic(gas_price, midterm_months, market_drawdown)
        f4 = FactorResult(
            name="domestic_pressure",
            value=f4_value,
            details={
                "gas_price": gas_price,
                "midterm_months": midterm_months,
                "market_drawdown": market_drawdown,
            }
        )

        # Factor 5: Polymarket calibration
        our_prob = base_rate  # Preliminary estimate
        f5_value = 0.0
        polymarket_divergence = None
        if polymarket_prob is not None:
            divergence = abs(polymarket_prob - our_prob)
            polymarket_divergence = divergence
            if divergence > 0.25:
                # Significant divergence — Polymarket has signal
                f5_value = (polymarket_prob - our_prob) * 0.05
            elif divergence > 0.15:
                f5_value = (polymarket_prob - our_prob) * 0.03
        f5 = FactorResult(
            name="polymarket_calibration",
            value=f5_value,
            weight=0.05,
            details={
                "polymarket_prob": polymarket_prob,
                "our_prob": our_prob,
                "divergence": polymarket_divergence,
                "large_divergence_flag": polymarket_divergence > 0.25 if polymarket_divergence else False,
            }
        )

        # Combined probability calculation
        # P = Factor1 × (1 + 0.25×Factor2) × (1 + Factor3) × (1 + Factor4) × (1 + 0.05×Factor5)
        prob = base_rate
        prob *= (1 + 0.25 * f2_value)
        prob *= (1 + f3_value)
        prob *= (1 + f4_value)
        prob *= (1 + 0.05 * f5_value)

        # Cap at reasonable range
        prob = min(max(prob, 0.05), 0.98)

        # Desensitization multiplier
        desensitization_mult = self.DESENSITIZATION_BASE ** (nth_similar_threat - 1)

        # Desensitized return
        desensitized_return = None
        if base_return is not None:
            desensitized_return = base_return * desensitization_mult

        # Confidence based on Factor 5 divergence
        confidence = 0.85
        if polymarket_divergence and polymarket_divergence > 0.25:
            confidence = 0.70

        return FiveFactorResult(
            probability=round(prob, 3),
            confidence=confidence,
            factor_1=f1,
            factor_2=f2,
            factor_3=f3,
            factor_4=f4,
            factor_5=f5,
            desensitization_multiplier=desensitization_mult,
            desensitized_return=round(desensitized_return, 2) if desensitized_return else None,
        )

    def _factor_2_market_pain(self, vix_current: float) -> float:
        """Calculate Factor 2: Market pain based on VIX level."""
        for threshold, value in self.VIX_THRESHOLDS:
            if vix_current > threshold:
                return value
        return 0.1  # Default low pain

    def _factor_4_domestic(
        self,
        gas_price: float,
        midterm_months: int,
        market_drawdown: float,
    ) -> float:
        """Calculate Factor 4: Domestic political pressure."""
        pressure = 0.0
        if gas_price > 4.0:
            pressure += self.DOMESTIC_TRIGGERS["gas_above_4"]
        if midterm_months < 6:
            pressure += self.DOMESTIC_TRIGGERS["midterm_within_6m"]
        if market_drawdown > 5.0:
            pressure += self.DOMESTIC_TRIGGERS["market_down_5pct"]
        return pressure

    def probability_at_day(
        self,
        base_prob: float,
        day: int,
        statement_type: StatementType,
    ) -> float:
        """
        Time-decayed reversal probability.

        For TRADE_TARIFF: peak at day 7, then decay
        For MILITARY: slower decay, lower peak
        """
        if statement_type == StatementType.TRADE_TARIFF:
            peak_day = 7
            decay = 0.92
        elif statement_type == StatementType.MILITARY:
            peak_day = 14
            decay = 0.97
        else:
            peak_day = 10
            decay = 0.95

        if day <= peak_day:
            return base_prob * (1 + 0.02 * day)
        else:
            return base_prob * (decay ** (day - peak_day))


# Convenience function
def calculate_reversal_probability(
    statement_type: StatementType,
    vix_current: float,
    counterparty_signal: str = "neutral",
    gas_price: float = 3.50,
    midterm_months: int = 12,
    market_drawdown: float = 0.0,
    polymarket_prob: Optional[float] = None,
    nth_similar_threat: int = 1,
    base_return: Optional[float] = None,
) -> FiveFactorResult:
    """Convenience wrapper for FiveFactorModel.calculate()."""
    model = FiveFactorModel()
    return model.calculate(
        statement_type=statement_type,
        vix_current=vix_current,
        counterparty_signal=counterparty_signal,
        gas_price=gas_price,
        midterm_months=midterm_months,
        market_drawdown=market_drawdown,
        polymarket_prob=polymarket_prob,
        nth_similar_threat=nth_similar_threat,
        base_return=base_return,
    )
