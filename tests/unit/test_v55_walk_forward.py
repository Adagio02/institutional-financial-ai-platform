import numpy as np
import pandas as pd
from finai.domain.qualification.v55_walk_forward import normalize_ensemble, build_purged_folds, simulate_walk_forward, qualify_walk_forward

def test_v55_purged_cost_aware_walk_forward():
    rng=np.random.default_rng(550); rows=[]; symbols=list("ABCDEF")
    for date in pd.date_range("2026-01-01",periods=18,tz="UTC"):
        alpha=rng.normal(size=6)
        for symbol,a in zip(symbols,alpha): rows.append({"timestamp":date,"symbol":symbol,"alpha__ensemble":a,"forward_return":.003*a+rng.normal(0,.0002)})
    frame=normalize_ensemble(pd.DataFrame(rows)); folds=build_purged_folds(frame)
    assert all(pd.Timestamp(f["train_end"]) < pd.Timestamp(f["test_start"]) for f in folds)
    returns,positions=simulate_walk_forward(frame,folds,transaction_cost_bps=5)
    assert len(returns)>0 and len(positions)>0
    assert (returns["net_return"] <= returns["gross_return"] + 1e-15).all()
    metrics=qualify_walk_forward(returns)
    assert metrics["fold_count"] >= 2
