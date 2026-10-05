"""Research kit: pre-registered hypotheses, one-shot historical tests, new SEC data,
and forward (shadow) testing of frozen strategies. Run from the project root:

    python -m research_kit --help
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path.cwd()
RESEARCH = ROOT / "research"
DATA = ROOT / "data" / "research" / "v56-expanded"

_src = ROOT / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
