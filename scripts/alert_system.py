"""
scripts/alert_system.py — TACO Alert System with Webhooks

Sends alerts to Slack, Discord, or other webhook endpoints.
Integrates with realtime_monitor.py for real-time notifications.

Usage:
    python scripts/alert_system.py --test --webhook-url "https://..."
    python scripts/alert_system.py --config alerts_config.json
    python scripts/alert_system.py --event TACO-011 --level warning
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "data" / "alerts_config.json"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class WebhookPlatform(Enum):
    """Supported webhook platforms."""
    SLACK = "slack"
    DISCORD = "discord"
    GENERIC = "generic"


@dataclass
class TACOAlert:
    """TACO alert message."""
    level: AlertLevel
    title: str
    message: str
    statement_id: Optional[str] = None
    probability: Optional[float] = None
    target: Optional[str] = None
    statement_type: Optional[str] = None
    timestamp: str = None
    fields: Optional[dict] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_slack(self) -> dict:
        """Convert to Slack webhook message."""
        color_map = {
            AlertLevel.INFO: "#36a64f",
            AlertLevel.WARNING: "#ff9900",
            AlertLevel.CRITICAL: "#ff0000",
            AlertLevel.EMERGENCY: "#000000",
        }

        fields = []
        if self.statement_id:
            fields.append({"title": "Statement", "value": self.statement_id, "short": True})
        if self.target:
            fields.append({"title": "Target", "value": self.target, "short": True})
        if self.statement_type:
            fields.append({"title": "Type", "value": self.statement_type, "short": True})
        if self.probability is not None:
            fields.append({"title": "TACO Probability", "value": f"{self.probability:.1%}", "short": True})

        attachment = {
            "color": color_map.get(self.level, "#36a64f"),
            "title": self.title,
            "text": self.message,
            "footer": "TACO Investment Intelligence",
            "ts": int(datetime.fromisoformat(self.timestamp).timestamp()),
        }

        if fields:
            attachment["fields"] = fields

        return {
            "text": f"*TACO Alert: {self.level.value.upper()}*",
            "attachments": [attachment],
        }

    def to_discord(self) -> dict:
        """Convert to Discord webhook message."""
        color_map = {
            AlertLevel.INFO: 0x36A64F,
            AlertLevel.WARNING: 0xFF9900,
            AlertLevel.CRITICAL: 0xFF0000,
            AlertLevel.EMERGENCY: 0x000000,
        }

        fields = []
        if self.statement_id:
            fields.append({"name": "Statement", "value": self.statement_id, "inline": True})
        if self.target:
            fields.append({"name": "Target", "value": self.target, "inline": True})
        if self.statement_type:
            fields.append({"name": "Type", "value": self.statement_type, "inline": True})
        if self.probability is not None:
            fields.append({"name": "TACO Probability", "value": f"{self.probability:.1%}", "inline": True})

        embed = {
            "title": self.title,
            "description": self.message,
            "color": color_map.get(self.level, 0x36A64F),
            "footer": {"text": "TACO Investment Intelligence"},
            "timestamp": self.timestamp,
        }

        if fields:
            embed["fields"] = fields

        return {"embeds": [embed]}

    def to_generic(self) -> dict:
        """Convert to generic JSON message."""
        return asdict(self)


class AlertSystem:
    """
    TACO Alert System for sending webhook notifications.

    Supports:
    - Slack webhooks
    - Discord webhooks
    - Generic HTTP webhooks
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_FILE
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load alert configuration."""
        if not self.config_path.exists():
            return {"webhooks": []}

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_config(self):
        """Save alert configuration."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def add_webhook(
        self,
        name: str,
        url: str,
        platform: WebhookPlatform = WebhookPlatform.SLACK,
        enabled: bool = True,
        min_level: AlertLevel = AlertLevel.WARNING,
    ):
        """Add a webhook endpoint."""
        webhook = {
            "name": name,
            "url": url,
            "platform": platform.value,
            "enabled": enabled,
            "min_level": min_level.value,
        }

        # Remove existing with same name
        self.config["webhooks"] = [
            w for w in self.config.get("webhooks", []) if w["name"] != name
        ]
        self.config["webhooks"].append(webhook)
        self._save_config()

        print(f"Added webhook: {name} ({platform.value})")

    def remove_webhook(self, name: str):
        """Remove a webhook endpoint."""
        self.config["webhooks"] = [
            w for w in self.config.get("webhooks", []) if w["name"] != name
        ]
        self._save_config()
        print(f"Removed webhook: {name}")

    def send_alert(self, alert: TACOAlert) -> dict:
        """Send alert to all configured webhooks."""
        results = {}

        for webhook in self.config.get("webhooks", []):
            if not webhook.get("enabled", True):
                continue

            # Check minimum level
            min_level = AlertLevel(webhook.get("min_level", "warning"))
            if alert.level.value < min_level.value:
                continue

            try:
                result = self._send_webhook(
                    url=webhook["url"],
                    platform=WebhookPlatform(webhook["platform"]),
                    payload=alert,
                )
                results[webhook["name"]] = {"success": True, "result": result}
            except Exception as e:
                results[webhook["name"]] = {"success": False, "error": str(e)}

        return results

    def _send_webhook(
        self,
        url: str,
        platform: WebhookPlatform,
        payload: TACOAlert,
    ) -> dict:
        """Send payload to a single webhook."""
        if platform == WebhookPlatform.SLACK:
            data = payload.to_slack()
        elif platform == WebhookPlatform.DISCORD:
            data = payload.to_discord()
        else:
            data = payload.to_generic()

        json_data = json.dumps(data).encode("utf-8")

        request = urllib.request.Request(
            url=url,
            data=json_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return {"status": response.status, "body": response.read().decode("utf-8")}
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code}: {e.read().decode('utf-8')}")
        except urllib.error.URLError as e:
            raise Exception(f"URL Error: {e.reason}")

    def test_webhook(self, url: str, platform: WebhookPlatform = WebhookPlatform.SLACK) -> bool:
        """Test a webhook endpoint."""
        test_alert = TACOAlert(
            level=AlertLevel.INFO,
            title="TACO Alert System Test",
            message="This is a test message from the TACO Investment Intelligence system.",
            statement_id="TEST-001",
            probability=0.75,
            target="Test Entity",
            statement_type="trade_tariff",
        )

        try:
            self._send_webhook(url, platform, test_alert)
            print(f"Test message sent successfully to {url}")
            return True
        except Exception as e:
            print(f"Failed to send test message: {e}")
            return False


# Convenience functions
def send_alert(
    level: AlertLevel,
    title: str,
    message: str,
    **kwargs
) -> dict:
    """Send an alert using default config."""
    system = AlertSystem()
    alert = TACOAlert(level=level, title=title, message=message, **kwargs)
    return system.send_alert(alert)


def send_taco_alert(
    statement_id: str,
    probability: float,
    level: AlertLevel,
    message: str,
    target: str = None,
    statement_type: str = None,
) -> dict:
    """Send a TACO-specific alert."""
    return send_alert(
        level=level,
        title=f"TACO Alert: {statement_id}",
        message=message,
        statement_id=statement_id,
        probability=probability,
        target=target,
        statement_type=statement_type,
    )


def main():
    parser = argparse.ArgumentParser(description="TACO Alert System")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Test webhook
    test_parser = subparsers.add_parser("test", help="Test a webhook endpoint")
    test_parser.add_argument("--webhook-url", required=True, help="Webhook URL")
    test_parser.add_argument(
        "--platform",
        choices=["slack", "discord", "generic"],
        default="slack",
        help="Webhook platform",
    )

    # Add webhook
    add_parser = subparsers.add_parser("add", help="Add a webhook endpoint")
    add_parser.add_argument("--name", required=True, help="Webhook name")
    add_parser.add_argument("--webhook-url", required=True, help="Webhook URL")
    add_parser.add_argument(
        "--platform",
        choices=["slack", "discord", "generic"],
        default="slack",
        help="Webhook platform",
    )
    add_parser.add_argument(
        "--min-level",
        choices=["info", "warning", "critical", "emergency"],
        default="warning",
        help="Minimum alert level",
    )

    # Remove webhook
    remove_parser = subparsers.add_parser("remove", help="Remove a webhook endpoint")
    remove_parser.add_argument("--name", required=True, help="Webhook name")

    # Send test alert
    send_parser = subparsers.add_parser("send", help="Send a test alert")
    send_parser.add_argument("--level", default="info", help="Alert level")
    send_parser.add_argument("--title", default="Test Alert", help="Alert title")
    send_parser.add_argument("--message", default="Test message", help="Alert message")

    # List webhooks
    list_parser = subparsers.add_parser("list", help="List configured webhooks")

    args = parser.parse_args()

    if args.command == "test":
        platform = WebhookPlatform(args.platform)
        system = AlertSystem()
        success = system.test_webhook(args.webhook_url, platform)
        sys.exit(0 if success else 1)

    elif args.command == "add":
        system = AlertSystem()
        system.add_webhook(
            name=args.name,
            url=args.webhook_url,
            platform=WebhookPlatform(args.platform),
            min_level=AlertLevel(args.min_level),
        )

    elif args.command == "remove":
        system = AlertSystem()
        system.remove_webhook(args.name)

    elif args.command == "send":
        alert = TACOAlert(
            level=AlertLevel(args.level),
            title=args.title,
            message=args.message,
        )
        system = AlertSystem()
        results = system.send_alert(alert)
        print(f"Sent alert to {len(results)} webhooks")

    elif args.command == "list":
        system = AlertSystem()
        webhooks = system.config.get("webhooks", [])
        if not webhooks:
            print("No webhooks configured.")
        else:
            print(f"Configured webhooks ({len(webhooks)}):")
            for w in webhooks:
                status = "✓" if w.get("enabled") else "✗"
                print(f"  {status} {w['name']} ({w['platform']}) - {w['url'][:50]}...")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
