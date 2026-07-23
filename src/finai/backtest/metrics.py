import numpy as np
import pandas as pd


def performance_metrics(returns: pd.Series, periods: int = 252) -> dict[str, float]:
    clean = returns.dropna()
    if clean.empty:
        return {}
    cumulative = (1 + clean).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1
    annual_return = cumulative.iloc[-1] ** (periods / len(clean)) - 1
    annual_vol = clean.std(ddof=1) * np.sqrt(periods)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0.0
    return {
        "annual_return": float(annual_return),
        "annual_volatility": float(annual_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(drawdown.min()),
        "hit_rate": float((clean > 0).mean()),
    }
