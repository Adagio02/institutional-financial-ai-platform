import argparse, json
from finai.research.v56.core import Config
from finai.research.v56.pipeline_v006 import run_pipeline_v006

p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",required=True)
p.add_argument("--minimum-symbols",type=int,default=30);p.add_argument("--cost-bps",type=float,default=5)
a=p.parse_args();cfg=Config(horizon=5,rebalance_every=5,min_symbols=a.minimum_symbols,cost_bps=a.cost_bps,
 long_fraction=.20,position_limit=.05,gross_limit=1.,ic_floor=.002,train_periods=756,min_train_periods=504,
 test_periods=63,embargo_periods=5,seed=29)
print(json.dumps(run_pipeline_v006(a.input,a.output,cfg),indent=2,default=str))
