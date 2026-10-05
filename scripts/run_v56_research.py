import argparse
import json

from finai.research.v56.core import Config
from finai.research.v56.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="artifacts/v56-research-003")
    parser.add_argument("--min-symbols", type=int, default=8)
    parser.add_argument("--cost-bps", type=float, default=5.0)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--rebalance-every", type=int, default=None,
                        help="periods between rebalances; defaults to --horizon (non-overlapping)")
    args = parser.parse_args()
    rebalance_every = args.rebalance_every if args.rebalance_every is not None else args.horizon
    cfg = Config(min_symbols=args.min_symbols, cost_bps=args.cost_bps, horizon=args.horizon,
                 rebalance_every=rebalance_every)
    print(json.dumps(run_pipeline(args.input, args.output, cfg), indent=2, default=str))


if __name__ == "__main__":
    main()

