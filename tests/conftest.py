import os


# Test isolation:
# Never allow the normal automated test suite to reach
# external Alpaca paper-trading or market-data services.
os.environ["EXECUTION_MODE"] = "sandbox"

os.environ["ALPACA_EXECUTION_ENABLED"] = "false"
os.environ["ALPACA_PAPER_TRADING_ENABLED"] = "false"

os.environ["ALPACA_TRADE_STREAM_ENABLED"] = "false"
os.environ["ALPACA_RECONCILIATION_ENABLED"] = "false"
os.environ["ALPACA_ORDER_DISCOVERY_ENABLED"] = "false"
os.environ["ALPACA_ORPHAN_RECOVERY_ENABLED"] = "false"