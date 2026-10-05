from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from finai.research.v56.v009_milestones import read_json, sha256, write_json_atomic, seal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--universe", required=True)
    parser.add_argument("--sector-attestation", required=True)
    parser.add_argument("--candidate-model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    protocol_path = Path(args.protocol)
    universe_path = Path(args.universe)
    attestation_path = Path(args.sector_attestation)
    protocol = read_json(protocol_path)
    attestation = read_json(attestation_path)
    universe = pd.read_csv(universe_path)

    provenance = universe["classification_provenance"].astype(str)
    if provenance.str.contains("seed|unverified", case=False, regex=True).any():
        raise RuntimeError("Sector universe still contains seed/unverified provenance")
    universe_hash = sha256(universe_path)
    if protocol.get("universe_sha256") != universe_hash:
        raise RuntimeError("Protocol universe hash does not match the active universe")
    if not attestation.get("verified") or attestation.get("universe_sha256") != universe_hash:
        raise RuntimeError("Sector attestation is absent, unverified, or for a different universe")

    policy = {
        "policy_version": "v009-shadow-milestones-1.0",
        "designation_at_13": "provisional_shadow_champion",
        "designation_at_26": "validated_shadow_monitoring",
        "official_lock_at_52": True,
        "milestones": [13, 26, 52],
        "horizon_trading_days": 5,
        "rebalance_every_trading_days": 5,
        "minimum_symbols": int(protocol.get("minimum_symbols", 80)),
        "interim_reports_performance_blind": True,
        "live_trading_allowed": False,
        "v57_unlocked": False,
        "champion_eligible": False,
        "policy_changes_allowed_after_start": False,
        "official_locked_rules": protocol["locked_rules"],
        "protocol_path": str(protocol_path),
        "protocol_sha256": sha256(protocol_path),
        "universe_path": str(universe_path),
        "universe_sha256": universe_hash,
        "sector_attestation_path": str(attestation_path),
        "sector_attestation_sha256": sha256(attestation_path),
        "candidate_model_path": str(Path(args.candidate_model)),
        "candidate_model_sha256": sha256(args.candidate_model),
        "prospective_lock_start": protocol["prospective_lock_start"],
    }
    output = write_json_atomic(args.output, policy, exclusive=True)
    digest = seal(output)
    print(f"Created immutable milestone policy: {output}")
    print(f"SHA256: {digest}")


if __name__ == "__main__":
    main()
