"""
Event Database for Uma Event Scanner – simplified & modernised.

Goals of this rewrite:
1. Remove any AI placeholder / unused complexity.
2. Support multiple data files (training events, support events, etc.) automatically.
3. Provide fuzzy matching using RapidFuzz (fast) with a clean fallback to
   Python's builtin difflib when RapidFuzz is not installed.
4. Keep the old public API used by the UI (find_matching_event, get_event_count…)
   so that other modules continue to work unchanged.
"""

# ruff: noqa: E501

from __future__ import annotations

import json
import re
from pathlib import Path
from event_scanner.utils.paths import get_data_dir
from typing import Dict, List, Optional, Set
from collections import defaultdict, Counter

from event_scanner.utils import Logger

try:
    from rapidfuzz import fuzz, process  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "RapidFuzz is required for high-accuracy matching. Install with 'pip install rapidfuzz'."
    ) from exc


DATA_DIR = get_data_dir()

# User yêu cầu chỉ dùng file training (đã bao phủ đủ)
SUPPORTED_FILES = ["events.json"]

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _normalise(text: str) -> str:
    """Lower-case, strip, and remove (❯) / ♪ plus extra whitespace."""
    text = text.lower()
    # Remove arrow & music note used in JP translations
    text = text.replace("(❯)", "").replace("♪", "")
    # Drop punctuation except spaces
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def _tokenise(text: str) -> List[str]:
    return [t for t in text.split() if t]


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class EventDatabase:
    """Load event definitions and perform fuzzy lookup from OCR text."""

    def __init__(self) -> None:
        # name -> list of event variants (each variant is dict with choices, sources, id, type)
        self._events: Dict[str, List[Dict]] = {}
        self._token_set: Set[str] = set()
        # Frequency of sources observed during session (updated externally)
        self._source_freq: Counter[str] = Counter()
        self.reload_events()

    # ----------------------------- public API -----------------------------
    def find_matching_event(self, texts: List[str], character_id_filter: Optional[str] = None) -> Optional[Dict]:
        """Return the best matching event dictionary or *None*.

        The algorithm:
        • Normalise combined OCR text.
        • Try for an exact or near-exact match (ratio ≥ 95).
        • Otherwise, pick the event with highest similarity ≥ 75.
        """
        if not texts:
            return None
        
        query = _normalise(" ".join(texts))
        if not query:
            return None

        # ------------------------------------------------------------
        # 1) Token-level spell-correction
        # ------------------------------------------------------------
        corrected_tokens: List[str] = []
        for tok in _tokenise(query):
            if tok in self._token_set:
                corrected_tokens.append(tok)
                continue

            # Find closest token in vocabulary
            suggestion, score, _ = process.extractOne(
                tok,
                self._token_set,
                scorer=fuzz.ratio,
            ) or (None, 0, None)

            corrected_tokens.append(suggestion if score >= 80 else tok)

        corrected_query = " ".join(corrected_tokens)

        # ------------------------------------------------------------
        # 2) Event-level fuzzy matching (token_set_ratio)
        # ------------------------------------------------------------
        # Get top candidates
        candidates = process.extract(
            corrected_query,
            list(self._events.keys()),
            scorer=fuzz.token_set_ratio,
            limit=10,
        )

        for cand_name, cand_score, _ in candidates:
            if cand_score < self.THRESHOLD_SCORE:
                break
            all_variants = self._events[cand_name]

            selected_variants = all_variants
            if character_id_filter:
                matches = [
                    v for v in all_variants
                    if any(
                        s.get('type') == 'character' and str(s.get('id', '')) == character_id_filter
                        for s in v.get('sources', [])
                    )
                ]
                Logger.debug(
                    f"Character id={character_id_filter}: {len(matches)} / {len(all_variants)} variants match (event='{cand_name}')"
                )
                if matches:
                    selected_variants = matches  # prefer variants matching character id

            # Choose from selected_variants
            if selected_variants:
                if len(selected_variants) == 1:
                    Logger.info(f"Matched event '{cand_name}' with score {cand_score:.1f}% (unique variant)")
                    return selected_variants[0]

                def variant_score(var: Dict):
                    srcs = var.get('sources', [])
                    if not srcs:
                        return 0
                    return max(self._source_freq.get(s.get('name',''),0) for s in srcs)

                variants_sorted = sorted(selected_variants, key=variant_score, reverse=True)
                chosen = variants_sorted[0]
                first_source = chosen.get('sources', [])
                first_name = first_source[0]['name'] if first_source else '?'
                Logger.info(
                    f"Matched event '{cand_name}' ({len(selected_variants)} variants) – chosen source {first_name} with score {cand_score:.1f}%"
                )
                return chosen

        Logger.debug(
            f"No event matched (query='{corrected_query}', original='{query}')"
        )
        return None
    
    def get_event_count(self) -> int:
        return len(self._events)

    # ------------------- session source frequency -------------------

    def increment_source(self, source_name: str):
        """Tăng bộ đếm tần suất cho nguồn *source_name*."""
        self._source_freq[source_name] += 1

    def reset_source_freq(self):
        """Xóa bộ đếm nguồn (khi bắt đầu nhân vật/scenario mới)."""
        self._source_freq.clear()

    def get_all_events(self) -> Dict[str, Dict]:
        return self._events.copy()

    def reload_events(self) -> None:
        """Clear and reload events from disk."""
        self._events.clear()
        self._token_set.clear()
        loaded_files = 0

        for file_name in SUPPORTED_FILES:
            path = DATA_DIR / file_name
            if not path.exists():
                Logger.warning(f"Event data file missing: {path}")
                continue

            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception as exc:  # pragma: no cover
                Logger.error(f"Failed to read {path}: {exc}")
                continue

            # Build mapping event_id -> sources first
            id_to_sources = self._extract_sources(data)
            self._process_file(data, id_to_sources)
            loaded_files += 1

        Logger.info(
            f"Loaded {self.get_event_count()} events / {len(self._token_set)} tokens from {loaded_files} file(s)"
        )

    # --------------------------- internal helpers -------------------------

    # Matching threshold for event similarity
    THRESHOLD_SCORE = 85  # Adjust this value to make matching stricter (0-100)

    def _process_file(self, data: object, id_to_sources: Dict[str,List[Dict]]) -> None:
        """Extract events from *data* in different shapes.

        The scraper output is structured with a top-level key `events` for
        training-event files.  Other files already contain a list at top level.
        """
        if isinstance(data, dict) and "events" in data:
            iterable = data["events"]
        elif isinstance(data, list):
            iterable = data
        else:
            Logger.warning("Unexpected JSON format; skipping file")
            return
        
        for entry in iterable:
            name = entry.get("event") or entry.get("name") or ""
            if not name:
                continue

            norm_name = _normalise(name)
            # Discard JP events entirely (heuristic)
            if not re.search(r"[a-z]", norm_name):
                continue

            event_id = entry.get("id") or entry.get("eventId") or ""
            if not event_id:
                Logger.warning(f"Event entry missing ID: {entry}")
                continue

            event_obj = {
                "name": name,
                "choices": entry.get("choices", []),
                "type": entry.get("type", "Unknown"),
                "sources": id_to_sources.get(event_id, []),
                "id": event_id,
            }

            self._events.setdefault(norm_name, []).append(event_obj)

            # Add tokens to vocabulary
            self._token_set.update(_tokenise(norm_name))

    # -------------------------------------------------------------------
    def _extract_sources(self, data: object) -> Dict[str, List[Dict]]:
        """Return mapping of eventId -> list of source dicts."""
        sources_map: Dict[str, List[Dict]] = defaultdict(list)

        if not isinstance(data, dict):
            return sources_map

        def add_source(section: str, entry_type: str):
            for ent in data.get(section, []):
                src_name = ent.get("name") or ent.get("id", "Unknown")
                src_id = str(ent.get("id", ""))
                for group in ent.get("eventGroups", []):
                    for eid in group.get("eventIds", []):
                        sources_map[eid].append({"type": entry_type, "name": src_name, "id": src_id})

        add_source("characters", "character")
        add_source("supportCards", "support")
        add_source("scenarios", "scenario")

        return sources_map


__all__ = ["EventDatabase"] 