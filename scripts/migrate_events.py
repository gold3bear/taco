"""
scripts/migrate_events.py — Migrate taco_events.csv to statements.json

Converts the legacy TACO event database to the new Statement model format
for the statement-driven TACO architecture.

Usage:
    python scripts/migrate_events.py
    python scripts/migrate_events.py --dry-run
"""

import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.statement import (
    Statement,
    StatementType,
    RhetoricIntensity,
    StatementStatus,
    InitialReaction,
    ReversalInfo,
    TYPE_ASSET_MAP,
)


# Category to StatementType mapping
CATEGORY_TO_TYPE = {
    "trade_tariff": StatementType.TRADE_TARIFF,
    "military_geopolitical": StatementType.MILITARY,
    "geopolitical": StatementType.TERRITORIAL,
    "domestic_policy": StatementType.POLICY,
    "tech_ban": StatementType.PERSONNEL,
    "sanctions": StatementType.SANCTIONS,
    "diplomatic": StatementType.DIPLOMATIC,
}

# Rhetoric intensity inferred from backdown_type
INTENSITY_MAP = {
    "90-day pause": RhetoricIntensity.HARD,
    "explicit walkback": RhetoricIntensity.HARD,
    "negotiated partial deal": RhetoricIntensity.MEDIUM,
    "negotiated partial deal ": RhetoricIntensity.MEDIUM,
    "dropped from agenda": RhetoricIntensity.SOFT,
    "rhetoric softened, no action taken": RhetoricIntensity.SOFT,
    "tariff reduction + 90-day truce": RhetoricIntensity.MEDIUM,
    "1-month reprieve": RhetoricIntensity.MEDIUM,
    "pause pending cooperation": RhetoricIntensity.MEDIUM,
    "75-day executive order extension": RhetoricIntensity.MEDIUM,
    "modified position, support maintained": RhetoricIntensity.MEDIUM,
    "selective exemptions for allies": RhetoricIntensity.MEDIUM,
    "implementation delayed": RhetoricIntensity.MEDIUM,
    "PENDING — current event": RhetoricIntensity.EXTREME,
    "Geneva deal — 90-day reduction to 30%": RhetoricIntensity.MEDIUM,
}

# Target entity extraction patterns
TARGET_PATTERNS = {
    "China": ["china", "chinese", "beijing"],
    "Mexico": ["mexico", "mexican"],
    "Canada": ["canada", "canadian"],
    "EU": ["european union", " eu ", "europe"],
    "Iran": ["iran", "iranian", "tehran"],
    "Russia": ["russia", "russian", "moscow"],
    "Ukraine": ["ukraine", "ukrainian", "kiev"],
    "Panama": ["panama", "panama canal"],
    "Greenland": ["greenland", "denmark", "danish"],
    "TikTok": ["tiktok", "bytedance"],
    "Federal Reserve": ["fed", "federal reserve", "powell", "jerome"],
    "Pharmaceutical": ["pharmaceutical", "drug", "medicine"],
    "EU": ["eu ", "european", "europe"],
    "Global": ["all imports", "global", "worldwide"],
}


def extract_target(description: str, category: str) -> str:
    """Extract target entity from event description."""
    desc_lower = description.lower()

    # Special cases by category
    if category == "tech_ban":
        return "TikTok"
    if category == "domestic_policy":
        if "fed" in desc_lower or "powell" in desc_lower:
            return "Federal Reserve"
        return "Domestic"
    if category == "military_geopolitical":
        if "iran" in desc_lower:
            return "Iran"
        if "ukraine" in desc_lower or "russia" in desc_lower:
            return "Ukraine"
    if category == "geopolitical":
        if "greenland" in desc_lower:
            return "Greenland"
        if "panama" in desc_lower:
            return "Panama"
    if category == "trade_tariff":
        if "china" in desc_lower:
            return "China"
        if "mexico" in desc_lower:
            return "Mexico"
        if "canada" in desc_lower:
            return "Canada"
        if "eu " in desc_lower or "europe" in desc_lower:
            return "EU"
        if "all imports" in desc_lower or "global" in desc_lower:
            return "Global"
        if "steel" in desc_lower or "aluminum" in desc_lower:
            return "Global Steel/Aluminum"
        if "pharmaceutical" in desc_lower or "drug" in desc_lower:
            return "Pharmaceutical"
        return "Global"

    # Generic search
    for target, patterns in TARGET_PATTERNS.items():
        for pattern in patterns:
            if pattern in desc_lower:
                return target

    return "Unknown"


def infer_statement_type(category: str) -> StatementType:
    """Map category to StatementType."""
    return CATEGORY_TO_TYPE.get(category, StatementType.MILITARY)


def infer_intensity(backdown_type: str, status: StatementStatus) -> RhetoricIntensity:
    """Infer rhetoric intensity from backdown type."""
    if status == StatementStatus.ACTIVE:
        return RhetoricIntensity.EXTREME

    normalized = backdown_type.lower().strip()
    return INTENSITY_MAP.get(normalized, RhetoricIntensity.MEDIUM)


def calculate_nth_similar(
    category: str,
    target: str,
    threat_date: datetime,
    all_events: list,
) -> int:
    """Calculate which occurrence this is of similar threats."""
    count = 1
    for event in all_events:
        event_date = parse_date(event.get("threat_date", ""))
        if event_date is None or event_date >= threat_date:
            break
        event_target = extract_target(event.get("description", ""), event.get("category", ""))
        if event.get("category") == category and event_target == target:
            count += 1
    return count


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str or date_str.strip() == "":
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def migrate_event(
    event: dict,
    all_events: list,
    existing_ids: set,
) -> Statement:
    """Convert a single taco_events.csv row to Statement model."""
    event_id = event["event_id"]
    threat_date = parse_date(event["threat_date"])
    backdown_date = parse_date(event["backdown_date"])
    category = event.get("category", "military_geopolitical")
    backdown_type = event.get("backdown_type", "")
    description = event.get("description", "")

    # Determine status
    if backdown_date:
        status = StatementStatus.REVERSED
    elif "PENDING" in backdown_type:
        status = StatementStatus.ACTIVE
    else:
        status = StatementStatus.AMBIGUOUS

    # Statement type
    statement_type = infer_statement_type(category)

    # Target entity
    target_entity = extract_target(description, category)

    # Rhetoric intensity
    intensity = infer_intensity(backdown_type, status)

    # Has deadline
    duration_days = event.get("duration_days", "")
    has_deadline = bool(duration_days and float(duration_days) < 90)

    # Deadline date
    deadline_date = None
    if has_deadline and threat_date and duration_days:
        try:
            deadline_date = threat_date + timedelta(days=float(duration_days))
        except (ValueError, TypeError):
            pass

    # Nth similar threat
    nth_similar = calculate_nth_similar(category, target_entity, threat_date, all_events)

    # Initial reaction
    initial_reaction = None
    try:
        initial_reaction = InitialReaction(
            sp500_return=float(event.get("sp500_threat_day_pct") or 0),
            nasdaq_return=float(event.get("nasdaq_threat_day_pct") or 0),
            oil_return=float(event.get("oil_threat_day_pct") or 0),
            btc_return=float(event.get("btc_threat_day_pct") or 0),
            vix_change=float(event.get("vix_spike_pct") or 0),
        )
    except (ValueError, TypeError):
        pass

    # Reversal info
    reversal_info = None
    if backdown_date and threat_date:
        try:
            days_to_reversal = (backdown_date - threat_date).days
        except (ValueError, TypeError):
            days_to_reversal = None

        reversal_info = ReversalInfo(
            reversal_date=backdown_date,
            reversal_type=backdown_type.strip() if backdown_type else None,
            days_to_reversal=days_to_reversal,
            rebound_magnitude=float(event.get("rebound_magnitude_pct") or 0),
        )

    # Generate unique ID if needed
    if event_id in existing_ids:
        new_id = f"{event_id}-migrated"
    else:
        new_id = event_id

    return Statement(
        id=new_id,
        raw_text=description,
        source="news_report",
        published_at=threat_date or datetime.now(),
        statement_type=statement_type,
        rhetoric_intensity=intensity,
        target_entity=target_entity,
        target_assets=TYPE_ASSET_MAP.get(statement_type, ["SPY"]),
        has_deadline=has_deadline,
        deadline_date=deadline_date,
        nth_similar_threat=nth_similar,
        status=status,
        initial_reaction=initial_reaction,
        reversal_info=reversal_info,
    )


def load_taco_events(csv_path: Path) -> list[dict]:
    """Load events from taco_events.csv."""
    events = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append(row)
    return events


def migrate_all(
    csv_path: Path,
    output_path: Path,
    dry_run: bool = False,
) -> list[Statement]:
    """Migrate all events from CSV to statements.json."""
    print(f"Loading events from {csv_path}...")
    events = load_taco_events(csv_path)
    print(f"Found {len(events)} events")

    print("Migrating events...")
    migrated = []
    existing_ids = set()

    for event in events:
        try:
            stmt = migrate_event(event, events, existing_ids)
            migrated.append(stmt)
            existing_ids.add(stmt.id)
        except Exception as e:
            print(f"Error migrating {event.get('event_id', 'unknown')}: {e}")

    print(f"Successfully migrated {len(migrated)} statements")

    # Print summary by type
    type_counts = {}
    for stmt in migrated:
        t = stmt.statement_type.value
        type_counts[t] = type_counts.get(t, 0) + 1
    print("\nStatements by type:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")

    # Print status counts
    status_counts = {}
    for stmt in migrated:
        s = stmt.status.value
        status_counts[s] = status_counts.get(s, 0) + 1
    print("\nStatements by status:")
    for s, count in sorted(status_counts.items()):
        print(f"  {s}: {count}")

    if not dry_run:
        print(f"\nWriting to {output_path}...")
        statements_data = [stmt.to_dict() for stmt in migrated]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(statements_data, f, indent=2, ensure_ascii=False)

        print(f"Successfully wrote {len(statements_data)} statements to {output_path}")
    else:
        print("\n[Dry run] - No files written")
        print("\nSample migration:")
        if migrated:
            sample = migrated[0]
            print(f"  {sample.id}: {sample.statement_type.value} targeting {sample.target_entity}")
            print(f"    Status: {sample.status.value}")
            print(f"    Intensity: {sample.rhetoric_intensity.value}")

    return migrated


def main():
    parser = argparse.ArgumentParser(description="Migrate taco_events.csv to statements.json")
    parser.add_argument(
        "--csv",
        type=str,
        default="data/taco_events.csv",
        help="Path to taco_events.csv (default: data/taco_events.csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/statements.json",
        help="Output path for statements.json (default: data/statements.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print migration plan without writing files",
    )

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / args.csv
    output_path = base_dir / args.output

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    migrate_all(csv_path, output_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
