import numpy as np
from finai.research.v56.core import Config
from finai.research.v56.portfolio import ranked_factor_neutral_weights


def test_ranked_constructor_is_active_and_neutral():
    sectors=np.repeat(["A","B","C","D"],5);beta=np.linspace(.7,1.3,20)
    scores=np.tile(np.array([-2.,-1.,0.,1.,2.]),4);vol=np.repeat(.02,20)
    weights,status=ranked_factor_neutral_weights(scores,np.zeros(20),Config(position_limit=.20),beta,sectors,vol)
    assert status=="active" and np.abs(weights).sum()>.1
    assert abs(weights.sum())<1e-8 and abs(weights@beta)<1e-8
    for sector in np.unique(sectors): assert abs(weights[sectors==sector].sum())<1e-8
