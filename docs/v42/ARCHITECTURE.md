# FinAI V4.2 Architecture

```text
ALPACA MARKET DATA
        |
        v
MARKET INGESTION
        |
        v
DATABASE
        |
        +-------------------+
        |                   |
        v                   v
      AAPL               SPY / QQQ
        |                   |
        +---------+---------+
                  |
                  v
         FEATURE ENGINEERING
                  |
                  v
         REGIME-AWARE MODELS
                  |
                  v
       PURGED WALK-FORWARD
                  |
                  v
       THRESHOLD CALIBRATION
                  |
                  v
       TRANSACTION-COST TEST
                  |
                  v
         UNTOUCHED HOLDOUT
                  |
             +----+----+
             |         |
           REJECT    QUALIFY
                       |
                       v
                    SHADOW
                       |
                       v
             PROSPECTIVE DATA
                       |
                  +----+----+
                  |         |
                REJECT    CHAMPION
                             |
                             v
                         PAPER MODE

ARTIFACTS
    |
    v
R / SHINY
    |
    +-- ggplot2
    +-- model metrics
    +-- risk/return
    +-- fold stability
    +-- governance state