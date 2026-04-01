"""
models/position_calculator.py — Two-Phase Position Calculator

Calculates position sizes for two-phase trading strategy:
- Phase 1: Follow initial market reaction (high certainty, low return)
- Phase 2: Reversal trades (medium certainty, high return, real alpha)
"""

from dataclasses import dataclass
from typing import Optional

from models.statement import StatementType


@dataclass
class TradeRecommendation:
    """Single trade recommendation."""
    phase: int                    # 1 or 2
    direction: str               # "long" or "short"
    asset: str                   # Ticker symbol
    size_pct: float              # Position size in percent
    entry_trigger: str           # Why we're entering
    hold_days_min: int
    hold_days_max: int
    exit_trigger: str            # Why we're exiting
    stop_trigger: str            # When to stop out
    expected_return: Optional[float] = None
    risk_reward_ratio: Optional[float] = None


@dataclass
class TwoPhaseResult:
    """Complete two-phase trading recommendation."""
    phase1: Optional[TradeRecommendation]
    phase2: Optional[TradeRecommendation]
    total_max_exposure: float
    reasoning: dict


# Type-specific risk multipliers
TYPE_RISK_MULTIPLIER = {
    StatementType.MILITARY: 0.5,      # Higher uncertainty
    StatementType.TRADE_TARIFF: 1.0,
    StatementType.PERSONNEL: 0.8,
    StatementType.TERRITORIAL: 0.7,
    StatementType.POLICY: 1.2,         # More predictable
    StatementType.SANCTIONS: 0.75,
    StatementType.DIPLOMATIC: 0.85,
}

# Asset reaction by type (approximate, in percent)
TYPE_ASSET_REACTIONS = {
    StatementType.TRADE_TARIFF: {
        "SPY": -2.1,
        "QQQ": -2.4,
        "XRT": -3.8,
        "TLT": +0.4,
        "DXY": +0.6,
    },
    StatementType.MILITARY: {
        "SPY": -1.8,
        "QQQ": -2.2,
        "USO": +4.5,
        "XLE": +3.8,
        "GLD": +1.5,
    },
    StatementType.TERRITORIAL: {
        "SPY": -0.5,
        "EEM": -1.8,
        "EFA": -1.2,
    },
    StatementType.PERSONNEL: {
        "SPY": -0.8,
        "XLF": -1.1,
        "GLD": +1.2,
    },
    StatementType.POLICY: {
        "SPY": -0.5,
        "TLT": +0.8,
        "DXY": +0.4,
    },
}


class TwoPhasePositionCalculator:
    """
    Calculates two-phase trading positions based on statement analysis.

    Phase 1: Initial reaction trading
    - Trigger: Statement published
    - Size: 2-3% (small, directional)
    - Hold: 1-3 days
    - Exit: Pain point OR 3 days passed

    Phase 2: Reversal trading
    - Trigger: Reversal signals detected
    - Size: reversal_prob × 10%, max 8%
    - Hold: Until confirmed OR 5 days
    - Exit: Reversal confirmed OR 5 days passed
    """

    PHASE1_CONFIG = {
        "size_pct": 2.5,
        "hold_days_min": 1,
        "hold_days_max": 3,
        "add_trigger_vix_spike": 5.0,  # Add 1-2% if VIX spikes >5%
        "add_size": 1.0,
        "max_total": 5.0,
    }

    PHASE2_CONFIG = {
        "size_formula_coef": 10.0,  # size = prob × 10
        "max_size_pct": 8.0,
        "hold_days_max": 5,
    }

    # Reversal signals and their probability boosts
    REVERSAL_SIGNALS = {
        "trump_says_great_progress": +0.25,
        "trump_says_they_called_me": +0.30,
        "trump_says_beautiful_deal": +0.35,
        "trump_says_we_talking": +0.20,
        "trump_extends_deadline": +0.15,
        "third_party_mediator_announces": +0.20,
        "counterparty_symbolic_concession": +0.25,
        "vix_drops_10pct_no_news": +0.15,
        "back_channel_rumor": +0.10,
    }

    # Anti-TACO signals (reduce reversal probability)
    ANTI_TACO_SIGNALS = {
        "new_harder_statement": -0.30,
        "military_action_confirmed": -0.45,
        "counterparty_hard_rejection": -0.20,
        "trump_says_no_deal_possible": -0.25,
        "ally_publicly_opposes_retreat": -0.15,
    }

    def calculate_phase1(
        self,
        statement_type: StatementType,
        predicted_return: float,
        vix_current: float,
    ) -> TradeRecommendation:
        """
        Calculate Phase 1 position: Follow initial reaction.

        Args:
            statement_type: Type of statement
            predicted_return: Predicted S&P 500 return (negative = market drops)
            vix_current: Current VIX level

        Returns:
            TradeRecommendation for Phase 1
        """
        # Direction: short if market drops, long if rises
        direction = "short" if predicted_return < 0 else "long"

        # Asset selection based on type
        asset = self._select_asset(statement_type, direction)

        # Size: 2.5% default, can add more on extreme pain
        size = self.PHASE1_CONFIG["size_pct"]

        # Entry: immediate on statement
        entry_trigger = "On statement publication, follow initial reaction"

        # Exit conditions
        exit_triggers = []
        if abs(predicted_return) > 2.0:
            exit_triggers.append("Pain threshold exceeded (add on spike)")
        exit_triggers.append(f"{self.PHASE1_CONFIG['hold_days_max']} days passed")

        return TradeRecommendation(
            phase=1,
            direction=direction,
            asset=asset,
            size_pct=size,
            entry_trigger=entry_trigger,
            hold_days_min=self.PHASE1_CONFIG["hold_days_min"],
            hold_days_max=self.PHASE1_CONFIG["hold_days_max"],
            exit_trigger=" OR ".join(exit_triggers),
            stop_trigger="Reversal signal detected → switch to Phase 2",
            expected_return=predicted_return,
        )

    def calculate_phase2(
        self,
        statement_type: StatementType,
        reversal_probability: float,
        reversal_signals_detected: dict,
        current_reversal_prob: float,
    ) -> Optional[TradeRecommendation]:
        """
        Calculate Phase 2 position: Bet on reversal.

        Only generate Phase 2 if:
        1. Reversal probability >= 35%
        2. At least one reversal signal is detected

        Args:
            statement_type: Type of statement
            reversal_probability: Current reversal probability from Five-Factor Model
            reversal_signals_detected: Dict of {signal_name: bool} for each known signal
            current_reversal_prob: Updated probability including signals

        Returns:
            TradeRecommendation for Phase 2, or None if conditions not met
        """
        # Check minimum probability threshold
        if current_reversal_prob < 0.35:
            return None

        # Check if any reversal signal is present
        signals_active = [k for k, v in reversal_signals_detected.items() if v]
        if not signals_active:
            return None

        # Calculate size: prob × 10%, capped at max
        base_size = current_reversal_prob * self.PHASE2_CONFIG["size_formula_coef"]
        type_risk = TYPE_RISK_MULTIPLIER.get(statement_type, 0.8)
        size = min(base_size * type_risk, self.PHASE2_CONFIG["max_size_pct"])

        # Direction: long (reversal = bet on recovery)
        direction = "long"

        # Asset: higher beta for reversal trades
        asset = self._select_asset(statement_type, "long")

        # Entry trigger
        signal_descriptions = [
            self.REVERSAL_SIGNALS.get(s, s) for s in signals_active
            if s in self.REVERSAL_SIGNALS
        ]
        entry_trigger = f"Reversal signal: {', '.join(signal_descriptions)}"

        # Calculate expected return (reversal typically recovers 1.5-3x initial move)
        expected_return = abs(reversal_signals_detected.get("_initial_return", 2.0)) * 1.8

        return TradeRecommendation(
            phase=2,
            direction=direction,
            asset=asset,
            size_pct=round(size, 1),
            entry_trigger=entry_trigger,
            hold_days_min=1,
            hold_days_max=self.PHASE2_CONFIG["hold_days_max"],
            exit_trigger="Reversal confirmed (S&P +2% day) OR 5 days passed",
            stop_trigger="Military action confirmed OR new harder statement",
            expected_return=round(expected_return, 1),
        )

    def calculate_two_phase(
        self,
        statement_type: StatementType,
        predicted_return: float,
        reversal_probability: float,
        vix_current: float,
        reversal_signals_detected: Optional[dict] = None,
        initial_return: Optional[float] = None,
    ) -> TwoPhaseResult:
        """
        Calculate complete two-phase trading recommendation.

        Args:
            statement_type: Type of statement
            predicted_return: Predicted S&P return from initial reaction
            reversal_probability: Base reversal probability from Five-Factor Model
            vix_current: Current VIX
            reversal_signals_detected: Dict of {signal: bool} for reversal signals
            initial_return: Actual initial return for Phase 2 sizing

        Returns:
            TwoPhaseResult with Phase 1 and Phase 2 recommendations
        """
        if reversal_signals_detected is None:
            reversal_signals_detected = {}

        # Update reversal probability based on detected signals
        updated_prob = reversal_probability
        for signal, detected in reversal_signals_detected.items():
            if detected and signal in self.REVERSAL_SIGNALS:
                updated_prob += self.REVERSAL_SIGNALS[signal]
            elif detected and signal in self.ANTI_TACO_SIGNALS:
                updated_prob += self.ANTI_TACO_SIGNALS[signal]
        updated_prob = min(max(updated_prob, 0.05), 0.98)

        # Add initial return to signals dict for Phase 2 calculation
        calc_signals = reversal_signals_detected.copy()
        if initial_return is not None:
            calc_signals["_initial_return"] = initial_return

        # Phase 1
        phase1 = self.calculate_phase1(
            statement_type=statement_type,
            predicted_return=predicted_return,
            vix_current=vix_current,
        )

        # Phase 2
        phase2 = self.calculate_phase2(
            statement_type=statement_type,
            reversal_probability=reversal_probability,
            reversal_signals_detected=calc_signals,
            current_reversal_prob=updated_prob,
        )

        # Total max exposure
        total_max = self.PHASE1_CONFIG["max_total"]
        if phase2:
            total_max += phase2.size_pct

        return TwoPhaseResult(
            phase1=phase1,
            phase2=phase2,
            total_max_exposure=min(total_max, 15.0),  # Hard cap at 15%
            reasoning={
                "statement_type": statement_type.value,
                "base_reversal_prob": reversal_probability,
                "updated_reversal_prob": round(updated_prob, 3),
                "signals_detected": [k for k, v in reversal_signals_detected.items() if v],
                "predicted_return": predicted_return,
                "type_risk_multiplier": TYPE_RISK_MULTIPLIER.get(statement_type, 0.8),
            }
        )

    def _select_asset(self, statement_type: StatementType, direction: str) -> str:
        """Select appropriate asset for statement type and direction."""
        reactions = TYPE_ASSET_REACTIONS.get(statement_type, {"SPY": -1.0})

        if direction == "short":
            # For short positions, pick asset that drops most
            return min(reactions.keys(), key=lambda x: reactions.get(x, 0))
        else:
            # For long positions, pick asset that rises most
            return max(reactions.keys(), key=lambda x: reactions.get(x, 0))


# Convenience function
def calculate_two_phase_position(
    statement_type: StatementType,
    predicted_return: float,
    reversal_probability: float,
    vix_current: float,
    reversal_signals_detected: Optional[dict] = None,
) -> TwoPhaseResult:
    """Convenience wrapper for TwoPhasePositionCalculator.calculate_two_phase()."""
    calc = TwoPhasePositionCalculator()
    return calc.calculate_two_phase(
        statement_type=statement_type,
        predicted_return=predicted_return,
        reversal_probability=reversal_probability,
        vix_current=vix_current,
        reversal_signals_detected=reversal_signals_detected,
    )
