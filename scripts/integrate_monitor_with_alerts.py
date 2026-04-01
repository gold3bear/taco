"""
scripts/integrate_monitor_with_alerts.py — Integrate Alerts with Real-time Monitor

This script shows how to connect the alert system with the real-time monitor
for automated notifications.

Usage:
    python scripts/integrate_monitor_with_alerts.py --daemon --alert-level warning
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.alert_system import AlertSystem, AlertLevel, send_taco_alert
from scripts.realtime_monitor import StatementMonitor


def run_monitor_with_alerts(
    poll_interval: int = 300,
    min_alert_level: AlertLevel = AlertLevel.WARNING,
):
    """
    Run the real-time monitor with alert integration.
    Sends alerts when probability changes significantly.
    """
    base_dir = Path(__file__).parent.parent
    monitor = StatementMonitor(base_dir / "data")
    alert_system = AlertSystem()

    print(f"Starting TACO monitor with alerts (poll interval: {poll_interval}s)")
    print(f"Minimum alert level: {min_alert_level.value}")

    last_probabilities = {}

    try:
        while True:
            print(f"\n[{datetime.now().isoformat()}] Running monitoring cycle...")

            # Run monitoring
            results = monitor.monitor_cycle()

            for result in results["results"]:
                statement_id = result["statement_id"]
                prob_update = result["probability_update"]
                detected_signals = result["detected_signals"]

                new_prob = prob_update["final_probability"]
                old_prob = last_probabilities.get(statement_id, 0.0)

                # Check if probability changed significantly
                prob_delta = abs(new_prob - old_prob)

                if prob_delta > 0.10:  # 10% threshold
                    # Determine alert level
                    if new_prob >= 0.70:
                        level = AlertLevel.CRITICAL
                    elif new_prob >= 0.50:
                        level = AlertLevel.WARNING
                    else:
                        level = AlertLevel.INFO

                    # Only send if above minimum level
                    if level.value >= min_alert_level.value:
                        # Build message
                        signal_names = [s.replace("_", " ") for s in detected_signals.keys()
                                       if not s.endswith("_source")]
                        message = (
                            f"TACO probability changed from {old_prob:.1%} to {new_prob:.1%} "
                            f"({prob_delta:+.1%})\n"
                            f"Signals: {', '.join(signal_names) if signal_names else 'None detected'}"
                        )

                        # Send alert
                        alert_result = send_taco_alert(
                            statement_id=statement_id,
                            probability=new_prob,
                            level=level,
                            message=message,
                        )

                        print(f"  Alert sent for {statement_id}: {new_prob:.1%}")

                last_probabilities[statement_id] = new_prob

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\nMonitor stopped.")


def main():
    parser = argparse.ArgumentParser(description="TACO Monitor with Alerts")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=300,
        help="Poll interval in seconds (default: 300 = 5 min)",
    )
    parser.add_argument(
        "--alert-level",
        choices=["info", "warning", "critical", "emergency"],
        default="warning",
        help="Minimum alert level to send",
    )

    args = parser.parse_args()

    run_monitor_with_alerts(
        poll_interval=args.poll_interval,
        min_alert_level=AlertLevel(args.alert_level),
    )


if __name__ == "__main__":
    main()
