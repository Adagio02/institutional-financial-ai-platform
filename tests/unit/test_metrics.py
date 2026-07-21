import pandas as pd
from finai.backtest.metrics import performance_metrics

def test_metrics_return_expected_keys():
    result = performance_metrics(pd.Series([0.01,-0.005,0.002]))
    assert "sharpe" in result
    assert "max_drawdown" in result
