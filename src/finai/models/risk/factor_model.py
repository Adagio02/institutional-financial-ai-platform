from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf
from sklearn.linear_model import Ridge

@dataclass(frozen=True)
class FactorRiskModel:
    exposures: pd.DataFrame
    factor_covariance: pd.DataFrame
    specific_variance: pd.Series

def estimate_factor_risk(
    asset_returns: pd.DataFrame,
    factor_returns: pd.DataFrame,
    ridge_alpha: float = 1.0,
) -> FactorRiskModel:
    aligned_assets, aligned_factors = asset_returns.align(factor_returns, join="inner", axis=0)
    exposure_rows = {}
    residual_vars = {}
    for asset in aligned_assets.columns:
        y = aligned_assets[asset].dropna()
        x = aligned_factors.loc[y.index].fillna(0.0)
        model = Ridge(alpha=ridge_alpha).fit(x, y)
        exposure_rows[asset] = model.coef_
        residual = y - model.predict(x)
        residual_vars[asset] = float(np.var(residual, ddof=1))
    exposures = pd.DataFrame.from_dict(
        exposure_rows, orient="index", columns=aligned_factors.columns
    )
    covariance = LedoitWolf().fit(aligned_factors.fillna(0.0)).covariance_
    factor_covariance = pd.DataFrame(
        covariance, index=aligned_factors.columns, columns=aligned_factors.columns
    )
    return FactorRiskModel(
        exposures=exposures,
        factor_covariance=factor_covariance,
        specific_variance=pd.Series(residual_vars),
    )
