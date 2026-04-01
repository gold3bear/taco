"""
scripts/realtime_monitor.py — Real-time Trump Statement Monitor

Monitors for new Trump statements and triggers analysis pipeline.
Updates reversal probabilities as new signals arrive.

Usage:
    python scripts/realtime_monitor.py --poll-interval 300  # 5 min
    python scripts/realtime_monitor.py --daemon
    python scripts/realtime_monitor.py --check-signals --statement-id TACO-011
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.statement import Statement, StatementType, StatementStatus
from models.five_factor import FiveFactorModel


# Reversal signal patterns and their probability impacts
REVERSAL_SIGNALS = {
    # Trump language signals
    "trump_says_great_progress": +0.25,
    "trump_says_they_called_me": +0.30,
    "trump_says_beautiful_deal": +0.35,
    "trump_says_we_talking": +0.20,
    "trump_extends_deadline": +0.15,
    "trump_drops_ultimatum": +0.20,

    # Counterparty signals
    "counterparty_symbolic_concession": +0.25,
    "third_party_mediator_announces": +0.20,
    "back_channel_rumor": +0.10,

    # Market signals
    "vix_drops_10pct_no_news": +0.15,
    "market_rally_without_catalyst": +0.10,
}

# Anti-TACO signals (reduce reversal probability)
ANTI_TACO_SIGNALS = {
    "new_harder_statement": -0.30,
    "military_action_confirmed": -0.45,
    "counterparty_hard_rejection": -0.20,
    "trump_says_no_deal_possible": -0.25,
    "ally_publicly_opposes_retreat": -0.15,
    "iran_enrichment_expansion": -0.30,
    "iran_military_mobilization": -0.25,
}

# Signal patterns to search for in news/text
SEARCH_PATTERNS = {
    # Trump de-escalation
    "great progress": "trump_says_great_progress",
    "they called me": "trump_says_they_called_me",
    "beautiful deal": "trump_says_beautiful_deal",
    "we are talking": "trump_says_we_talking",
    "we're talking": "trump_says_we_talking",
    "extend": "trump_extends_deadline",
    "pause": "trump_extends_deadline",
    # Counterparty
    "symbolic": "counterparty_symbolic_concession",
    "mediation": "third_party_mediator_announces",
    "talks resumed": "third_party_mediator_announces",
    # Anti-TACO
    "all options": "new_harder_statement",
    "military strike": "military_action_confirmed",
    "will never": "counterparty_hard_rejection",
    "no deal possible": "trump_says_no_deal_possible",
}


class BayesianUpdater:
    """
    Bayesian probability updater for reversal signals.
    Uses likelihood ratios to update probability.
    """

    # Likelihood ratios: P(signal | reversal occurs) / P(signal | reversal doesn't occur)
    LIKELIHOOD_RATIOS = {
        "trump_says_great_progress": 8.5,
        "trump_says_they_called_me": 12.0,
        "third_party_mediator_announces": 5.0,
        "vix_drops_10pct_no_news": 4.2,
        "counterparty_symbolic_concession": 6.5,
        "trump_extends_deadline": 3.8,
        "military_action_confirmed": 0.05,
        "counterparty_hard_rejection": 0.20,
        "new_harder_statement": 0.15,
        "trump_says_no_deal_possible": 0.10,
    }

    def __init__(self, prior_probability: float):
        self.prior = prior_probability
        self.history = []

    def update(self, signal: str) -> tuple[float, float]:
        """
        Update probability based on signal.
        Returns (new_probability, delta)
        """
        lr = self.LIKELIHOOD_RATIOS.get(signal, 1.0)

        # Bayesian update: posterior = lr * prior / (lr * prior + (1 - prior))
        posterior = (lr * self.prior) / (lr * self.prior + (1 - self.prior))
        posterior = min(max(posterior, 0.01), 0.99)

        delta = posterior - self.prior
        self.prior = posterior

        self.history.append({
            "signal": signal,
            "lr": lr,
            "prior_before": posterior - delta,
            "posterior": posterior,
            "delta": delta,
            "timestamp": datetime.now().isoformat(),
        })

        return posterior, delta


class StatementMonitor:
    """
    Monitor active statements for reversal signals.
    Updates probabilities and generates alerts.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.statements_file = data_dir / "statements.json"
        self.monitor_state_file = data_dir / "monitor_state.json"

    def load_statements(self) -> list[Statement]:
        """Load statements from database."""
        if not self.statements_file.exists():
            return []

        with open(self.statements_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [Statement.from_dict(s) for s in data]

    def get_active_statements(self) -> list[Statement]:
        """Get currently active statements."""
        statements = self.load_statements()
        return [s for s in statements if s.status == StatementStatus.ACTIVE]

    def load_monitor_state(self) -> dict:
        """Load monitoring state."""
        if not self.monitor_state_file.exists():
            return {"last_check": None, "probability_history": {}}

        with open(self.monitor_state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_monitor_state(self, state: dict):
        """Save monitoring state."""
        with open(self.monitor_state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def check_signals(self, statement_id: str, text: str) -> dict:
        """
        Check text for reversal/anti-TACO signals.
        Returns dict of detected signals.
        """
        text_lower = text.lower()
        detected = {}

        for pattern, signal_name in SEARCH_PATTERNS.items():
            if pattern.lower() in text_lower:
                if signal_name in REVERSAL_SIGNALS:
                    detected[signal_name] = True
                    detected[f"{signal_name}_source"] = text[:200]
                elif signal_name in ANTI_TACO_SIGNALS:
                    detected[signal_name] = True
                    detected[f"{signal_name}_source"] = text[:200]

        return detected

    def update_probability(
        self,
        statement_id: str,
        current_prob: float,
        signals: dict,
    ) -> dict:
        """
        Update probability based on detected signals.
        Returns updated probability and history.
        """
        updater = BayesianUpdater(current_prob)
        updates = []

        for signal, is_detected in signals.items():
            if is_detected and signal in REVERSAL_SIGNALS:
                new_prob, delta = updater.update(signal)
                updates.append({
                    "signal": signal,
                    "new_probability": new_prob,
                    "delta": delta,
                    "timestamp": datetime.now().isoformat(),
                })

        for signal, is_detected in signals.items():
            if is_detected and signal in ANTI_TACO_SIGNALS:
                new_prob, delta = updater.update(signal)
                updates.append({
                    "signal": signal,
                    "new_probability": new_prob,
                    "delta": delta,
                    "timestamp": datetime.now().isoformat(),
                    "is_anti_taco": True,
                })

        return {
            "final_probability": updater.prior,
            "updates": updates,
            "history": updater.history,
        }

    def generate_alert(
        self,
        statement: Statement,
        probability_update: dict,
    ) -> str:
        """Generate alert text for probability change."""
        current_prob = probability_update["final_probability"]
        updates = probability_update["updates"]

        if not updates:
            return ""

        alert = f"""
🚨 TACO MONITOR ALERT: {statement.id}
=====================================

**Target:** {statement.target_entity}
**Type:** {statement.statement_type.value}
**Current Reversal Probability:** {current_prob:.1%}

**Probability Update:**
"""
        for update in updates:
            direction = "⬆️" if update["delta"] > 0 else "⬇️"
            anti_tag = " [ANTI-TACO]" if update.get("is_anti_taco") else ""
            alert += f"- {direction} {update['signal']}{anti_tag}: {update['new_probability']:.1%} ({update['delta']:+.1%})\n"

        alert += f"""
**Recommended Action:**
"""
        if current_prob >= 0.70:
            alert += "- ✅ HIGH reversal probability — prepare for Phase 2 entry\n"
        elif current_prob >= 0.50:
            alert += "- ⚠️ MODERATE probability — monitor closely\n"
        elif current_prob >= 0.35:
            alert += "- 🔶 LOW-MODERATE probability — wait for more signals\n"
        else:
            alert += "- ❌ LOW reversal probability — avoid Phase 2\n"

        return alert

    def monitor_cycle(self, text_input: Optional[str] = None) -> dict:
        """
        Run a single monitoring cycle.
        If text_input is provided, check it for signals.
        Otherwise, check all active statements.
        """
        active = self.get_active_statements()
        state = self.load_monitor_state()

        results = []

        for statement in active:
            # Get current probability (from previous monitoring or default)
            prob_key = f"{statement.id}_prob"
            current_prob = state.get("probability_history", {}).get(
                statement.id,
                0.38 if statement.statement_type == StatementType.MILITARY else 0.50
            )

            # Check for signals
            signals = {}
            if text_input:
                signals = self.check_signals(statement.id, text_input)

            if signals:
                # Update probability
                prob_update = self.update_probability(
                    statement.id, current_prob, signals
                )

                # Save to history
                if statement.id not in state["probability_history"]:
                    state["probability_history"][statement.id] = []
                state["probability_history"][statement.id].append({
                    "probability": prob_update["final_probability"],
                    "timestamp": datetime.now().isoformat(),
                    "signals": [u["signal"] for u in prob_update["updates"]],
                })

                # Generate alert
                alert = self.generate_alert(statement, prob_update)

                results.append({
                    "statement_id": statement.id,
                    "probability_update": prob_update,
                    "detected_signals": signals,
                    "alert": alert,
                })

        state["last_check"] = datetime.now().isoformat()
        self.save_monitor_state(state)

        return {
            "checked_statements": len(active),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    parser = argparse.ArgumentParser(description="TACO Real-time Monitor")
    parser.add_argument("--poll-interval", type=int, default=300,
                        help="Poll interval in seconds (default: 300 = 5 min)")
    parser.add_argument("--daemon", action="store_true",
                        help="Run continuously as daemon")
    parser.add_argument("--check-signals", type=str,
                        help="Check specific text for signals")
    parser.add_argument("--statement-id", type=str,
                        help="Statement ID to monitor")

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    monitor = StatementMonitor(base_dir / "data")

    if args.daemon:
        print(f"Starting TACO monitor daemon (poll interval: {args.poll_interval}s)")
        print("Press Ctrl+C to stop")

        try:
            while True:
                print(f"\n[{datetime.now().isoformat()}] Running monitoring cycle...")
                results = monitor.monitor_cycle()
                print(f"Checked {results['checked_statements']} active statements")

                for result in results["results"]:
                    print(result["alert"])

                time.sleep(args.poll_interval)

        except KeyboardInterrupt:
            print("\nMonitor stopped.")

    elif args.check_signals:
        # Check text for signals
        text = args.check_signals

        if args.statement_id:
            active = monitor.get_active_statements()
            statement = next((s for s in active if s.id == args.statement_id), None)
            if not statement:
                print(f"Statement {args.statement_id} not found or not active")
                sys.exit(1)
        else:
            # Create dummy statement
            statement = Statement(
                id="CHECK",
                raw_text=text,
                source="manual",
                published_at=datetime.now(),
                statement_type=StatementType.MILITARY,
                rhetoric_intensity=None,
                target_entity="Unknown",
                target_assets=["SPY"],
                has_deadline=False,
            )

        print(f"Checking text for signals...")
        print(f"Text: {text[:200]}...")

        signals = monitor.check_signals(statement.id, text)

        if signals:
            print(f"\nDetected {len(signals)} signals:")
            for signal, detected in signals.items():
                if not signal.endswith("_source"):
                    print(f"  - {signal}: {detected}")

            # Update probability
            prob_update = monitor.update_probability(
                statement.id,
                0.38,  # Default military base
                signals
            )

            print(f"\nProbability update: {prob_update['final_probability']:.1%}")
            for update in prob_update["updates"]:
                print(f"  - {update['signal']}: {update['delta']:+.1%}")

            alert = monitor.generate_alert(statement, prob_update)
            print(alert)
        else:
            print("No signals detected.")

    else:
        # Single monitoring cycle
        results = monitor.monitor_cycle()
        print(f"Monitor cycle complete at {results['timestamp']}")
        print(f"Checked {results['checked_statements']} active statements")

        for result in results["results"]:
            print(result["alert"])


if __name__ == "__main__":
    main()
