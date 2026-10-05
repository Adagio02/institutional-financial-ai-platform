import numpy as np,pandas as pd
from finai.research.v56.pipeline_v008 import _residualize_target

def test_target_residualization_removes_sector_and_beta_exposure():
    sector=np.repeat(["A","B","C"],10);beta=np.linspace(.7,1.3,30)
    y=np.repeat([.02,-.01,.005],10)+.03*beta+np.tile(np.linspace(-.01,.01,10),3)
    frame=pd.DataFrame({"sector":sector,"beta":beta,"forward_return":y})
    residual=_residualize_target(frame);valid=residual.notna()
    assert abs(float(residual[valid] @ beta[valid]))<1e-8
    for name in np.unique(sector):assert abs(residual[sector==name].mean())<1e-8
