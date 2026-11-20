import argparse, json
from finai.research.v56.core import Config
from finai.research.v56.pipeline import run_pipeline

p=argparse.ArgumentParser(); p.add_argument("--input",required=True);p.add_argument("--output",required=True)
p.add_argument("--minimum-symbols",type=int,default=30);p.add_argument("--cost-bps",type=float,default=5)
a=p.parse_args()
cfg=Config(horizon=5,rebalance_every=5,min_symbols=a.minimum_symbols,cost_bps=a.cost_bps,
           position_limit=.04,gross_limit=1.0,turnover_penalty=.004,risk_penalty=10.0,
           train_periods=756,min_train_periods=504,test_periods=63,embargo_periods=5)
print(json.dumps(run_pipeline(a.input,a.output,cfg,version="5.6-research-005"),indent=2,default=str))
