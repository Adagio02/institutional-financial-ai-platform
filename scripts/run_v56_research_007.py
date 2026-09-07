import argparse,json
from finai.research.v56.core import Config
from finai.research.v56.pipeline_v007 import run_v007
p=argparse.ArgumentParser();p.add_argument("--predictions",required=True);p.add_argument("--output",required=True)
p.add_argument("--cost-bps",type=float,default=5);a=p.parse_args()
cfg=Config(horizon=5,rebalance_every=5,long_fraction=.20,gross_limit=1.,position_limit=.06,
 cost_bps=a.cost_bps,beta_exposure_limit=.10,rebalance_turnover_limit=.25,seed=29)
print(json.dumps(run_v007(a.predictions,a.output,cfg),indent=2,default=str))
