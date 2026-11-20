import numpy as np
from finai.research.v56.core import Config
from finai.research.v56.portfolio_v007 import alpha_preserving_weights


def test_alpha_preserving_constructor_respects_risk_and_turnover_bands():
    sectors=np.repeat(["A","B","C","D"],5);beta=np.linspace(.7,1.3,20)
    scores=np.tile(np.array([-2.,-1.,0.,1.,2.]),4);previous=np.zeros(20)
    cfg=Config(position_limit=.10,beta_exposure_limit=.10,rebalance_turnover_limit=.25)
    weights,status=alpha_preserving_weights(scores,previous,beta,sectors,cfg)
    assert status=="active" and abs(weights).sum()>0
    assert np.abs(weights-previous).sum()<=cfg.rebalance_turnover_limit+1e-8
    assert abs(weights.sum())<1e-8 and abs(weights@beta)<=cfg.beta_exposure_limit+1e-8
    for sector in np.unique(sectors): assert abs(weights[sectors==sector].sum())<1e-8
