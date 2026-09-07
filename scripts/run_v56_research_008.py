import argparse,json
from finai.research.v56.core import Config
from finai.research.v56.pipeline_v008 import run_v008
p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",required=True);p.add_argument("--cost-bps",type=float,default=5);a=p.parse_args()
cfg=Config(horizon=5,rebalance_every=5,min_symbols=30,long_fraction=.20,gross_limit=1.,position_limit=.06,
 cost_bps=a.cost_bps,beta_exposure_limit=.10,rebalance_turnover_limit=.25,ic_floor=.002,
 train_periods=756,min_train_periods=504,test_periods=63,embargo_periods=5,seed=41)
print(json.dumps(run_v008(a.input,a.output,cfg),indent=2,default=str))
