from typing import Dict, Set

# ============================================================
# SESSION STATE (in-memory)
# ============================================================
# These dicts are module-level singletons. All importers get a
# reference to the SAME object. Never reassign them; only mutate.

SESSION_START_TIMES: Dict[str, float] = {}
SESSION_TURN_COUNT: Dict[str, int] = {}
SESSION_SCAM_SCORE: Dict[str, int] = {}
SESSION_COUNTS: Dict[str, Dict[str, int]] = {}
SESSION_ASKED: Dict[str, Set[str]] = {}
FINAL_REPORTED: Set[str] = set()
