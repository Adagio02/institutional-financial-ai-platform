"""Compatibility entry point; V4.8.2 trains ranking models, not a freeze."""

from run_v482_ranking_models import result

assert result["version"] == "4.8.2"
