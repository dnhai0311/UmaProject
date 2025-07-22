#!/usr/bin/env python3
"""Check for duplicate events inside the same owner section in data/event.txt.
Run: python tools/check_duplicate_events.py
"""
import re
from pathlib import Path
from collections import defaultdict, Counter

TXT_PATH = Path(__file__).resolve().parents[1] / "data" / "event.txt"

if not TXT_PATH.exists():
    print(f"File not found: {TXT_PATH}")
    exit(1)

owners = {}
current_owner = None

owner_line_re = re.compile(r"^(Character|Support|Scenario):\s+(.*)$")

with TXT_PATH.open(encoding="utf-8") as fh:
    for line in fh:
        line = line.rstrip("\n")
        m = owner_line_re.match(line)
        if m:
            current_owner = m.group(2).strip()
            owners[current_owner] = []
            continue
        if current_owner and line.startswith("    - "):
            event_name = line[6:].strip()
            owners[current_owner].append(event_name)

has_dup = False
for owner, events in owners.items():
    duplicates = [evt for evt, cnt in Counter(events).items() if cnt > 1]
    if duplicates:
        has_dup = True
        print(f"Owner: {owner}")
        for evt in duplicates:
            print(f"  DUPLICATE x{events.count(evt)} -> {evt}")
        print()

if not has_dup:
    print("No duplicates found!") 