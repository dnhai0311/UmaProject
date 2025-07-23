#!/usr/bin/env python3
"""Detect fully duplicated events in data/events.json.

Two events are considered duplicates when *all* of the following are identical:
    • `event` name  (string)
    • `type`        (string)
    • complete `choices` array (order-sensitive deep-compare)

For every duplicate found, list where each duplicate ID is referenced
across characters, support cards and scenarios.

Run: python tools/check_duplicate_events.py
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Set

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "events.json"

if not DATA_PATH.exists():
    print(f"File not found: {DATA_PATH}")
    raise SystemExit(1)

# -------------------------------------------------------------
# Utility: create canonical key for an event (strict deep compare)
# -------------------------------------------------------------


def canonical_event_key(ev: Dict[str, Any]) -> str:
    """Return deterministic string key based on event content (excluding `id`)."""

    key_dict = {
        "event": ev.get("event"),
        "type": ev.get("type"),
        # choices with effects in given order
        "choices": ev.get("choices", []),
    }
    # Using ensure_ascii=False preserves non-ASCII chars for readability
    return json.dumps(key_dict, ensure_ascii=False, sort_keys=True)


# -------------------------------------------------------------
# Load JSON
# -------------------------------------------------------------

with DATA_PATH.open(encoding="utf-8") as fh:
    data = json.load(fh)

events: List[Dict[str, Any]] = data.get("events", [])


# -------------------------------------------------------------
# Build duplicate map: key -> list[event_id]
# -------------------------------------------------------------

dup_map: Dict[str, List[str]] = defaultdict(list)

for ev in events:
    key = canonical_event_key(ev)
    dup_map[key].append(ev["id"])

# Keep only duplicates (len>1)
duplicates: Dict[str, List[str]] = {k: ids for k, ids in dup_map.items() if len(ids) > 1}

if not duplicates:
    print("No fully duplicated events found.")
    raise SystemExit(0)


# -------------------------------------------------------------
# Build index: event_id -> list[(owner_type, owner_id)]
# -------------------------------------------------------------

id_to_owners: Dict[str, List[Tuple[str, str]]] = defaultdict(list)


def add_links(owner_type: str, owners: List[Dict[str, Any]]):
    for owner in owners:
        oid = owner.get("id")
        for group in owner.get("eventGroups", []):
            for ev_id in group.get("eventIds", []):
                id_to_owners[ev_id].append((owner_type, oid))


add_links("character", data.get("characters", []))
add_links("support", data.get("supportCards", []))
add_links("scenario", data.get("scenarios", []))


# -------------------------------------------------------------
# Report
# -------------------------------------------------------------

def format_owner_list(lst: List[Tuple[str, str]]) -> str:
    return ", ".join(f"{t}:{oid}" for t, oid in lst)


print("Detected duplicate events (fully identical):\n")

for key, ids in duplicates.items():
    # Use first event's data for display
    sample = next(ev for ev in events if ev["id"] == ids[0])
    print(f"- Event: {sample['event']}  |  Type: {sample['type']}")
    print(
        f"  Choices count: {len(sample.get('choices', []))}  |  Duplicate IDs ({len(ids)}): {', '.join(ids)}"
    )

    for ev_id in ids:
        owners = id_to_owners.get(ev_id, [])
        owner_str = format_owner_list(owners) if owners else "<unlinked>"
        print(f"    • {ev_id} referenced by: {owner_str}")
    print() 