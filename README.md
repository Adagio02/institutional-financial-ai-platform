# Institutional Financial AI Platform

A research-grade, enterprise-style financial intelligence platform built for an AI engineering portfolio.

It combines:

- Real-world public market, macroeconomic, factor, and SEC filing data
- Point-in-time-aware feature engineering
- Cross-sectional return ranking
- Volatility and tail-risk forecasting
- Institutional-style multifactor risk modeling
- Portfolio construction with exposure, turnover, and liquidity constraints
- Walk-forward backtesting with transaction costs
- MLflow experiment tracking
- SEC filing Retrieval-Augmented Generation
- FastAPI, Streamlit, R, PostgreSQL, Qdrant, MinIO, Prefect, and Tableau exports
- Automated testing, CI, observability, and deployment templates

## Important positioning

This system does **not** copy a proprietary bank or hedge-fund algorithm. It implements publicly documented techniques commonly used in institutional research:

- Fama–French-style systematic factors
- Cross-sectional ranking models
- Regularized factor exposure estimation
- Covariance shrinkage and risk decomposition
- Walk-forward validation
- Transaction-cost-aware portfolio optimization
- GARCH volatility modeling
- Monte Carlo and historical stress testing
- Model governance and explainability

The project is for research, simulation, and portfolio demonstration. It is not financial advice and does not promise profitability.

## Real-world data connectors

The repository includes connectors for:

- SEC EDGAR submissions and XBRL Company Facts
- FRED and ALFRED macroeconomic series
- Kenneth French factor datasets
- U.S. Treasury fiscal data
- Pluggable licensed market-data providers

Large datasets are downloaded by pipeline commands rather than committed to Git.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .[dev]

Copy-Item .env.example .env
docker compose up -d

python -m uvicorn src.finai.api.main:app --reload
```

In another terminal:

```powershell
.venv\Scripts\activate
python -m streamlit run apps/streamlit/app.py
```

Run validation:

```powershell
python scripts/check_structure.py
python -m compileall -q src apps tests
pytest
```

## Recommended implementation sequence

1. Configure `.env`.
2. Download FRED, SEC, Treasury, and factor data.
3. Add an approved market-data provider.
4. Build bronze, silver, and gold datasets.
5. Run point-in-time feature generation.
6. Train the cross-sectional alpha and volatility models.
7. Run walk-forward backtests.
8. Publish predictions and risk analytics to PostgreSQL.
9. Index SEC filings in Qdrant.
10. Open Streamlit and Tableau dashboards.

## Repository architecture

```text
Data sources
  ├─ SEC EDGAR
  ├─ FRED / ALFRED
  ├─ Kenneth French Data Library
  ├─ U.S. Treasury
  └─ Market-data provider
          ↓
Bronze immutable storage
          ↓
Silver normalized point-in-time datasets
          ↓
Gold features, labels, factors, forecasts
          ↓
  ┌───────┼─────────┬─────────────┐
  │       │         │             │
Alpha   Risk      Portfolio       RAG
models  models    optimizer       system
  │       │         │             │
  └───────┴─────────┴─────────────┘
          ↓
FastAPI · Streamlit · Tableau · MLflow
```

## Institutional-style model

The flagship model is a two-stage research pipeline:

1. **Expected-return model**
   - Cross-sectional ranking target
   - Momentum, quality, value, low-volatility, macro, and filing-derived features
   - Elastic-net baseline and gradient-boosted ranking model
   - Purged walk-forward validation

2. **Risk and portfolio model**
   - Multifactor exposure matrix
   - Shrunk factor covariance
   - Specific-risk estimates
   - Constrained mean-variance optimization
   - Turnover, liquidity, sector, beta, and position-size constraints
   - Transaction costs and market-impact approximation

This mirrors public institutional research practices without claiming access to proprietary methods.

## License

Apache-2.0. Review each external data source's license and usage terms before redistribution.
## Version 0.5

Version 0.5 adds a reproducible feature-engineering
and dataset platform.

### Feature capabilities

- Simple returns
- Logarithmic returns
- Rolling means
- Rolling standard deviation
- Annualized rolling volatility
- Momentum
- RSI
- MACD
- ATR
- Volume change
- Drawdown

### Dataset capabilities

- Versioned feature sets
- Persisted feature values
- Deterministic schema hashes
- Deterministic content hashes
- Parquet dataset output
- Dataset lineage and status
- Temporal-leakage tests

POST /api/v1/features/generate
GET  /api/v1/features/sets

POST /api/v1/datasets/build
GET  /api/v1/datasets
GET  /api/v1/datasets/{dataset_id}

## Version 0.6

Version 0.6 adds reproducible model training and
experiment tracking.

### Training capabilities

- Classification and regression tasks
- Logistic-regression baseline
- Linear-regression baseline
- Random-forest classification
- Random-forest regression
- Expanding walk-forward validation
- Fold-level and aggregate evaluation metrics
- Train-only preprocessing
- Deterministic random seeds

### Tracking and artifacts

- MLflow experiment tracking
- Persisted training-run records
- Persisted fold metrics
- Serialized Joblib model artifacts
- SHA-256 model artifact hashes
- Candidate, staging, production, rejected, and
  archived model stages

  ## Version 0.7

Version 0.7 adds governed prediction serving and model
explanations.

### Prediction serving

- Staging and production model serving
- Model artifact checksum verification
- Exact feature-schema validation
- Historical timestamp filtering
- Prediction persistence
- Model and dataset lineage
- Classification probabilities and confidence

### Governance

- Model cards
- Evaluation requirements
- Artifact validation
- Explicit staging-to-production promotion
- Configurable metric thresholds
- Controlled stage transitions

### Explanations

- Linear-model feature contributions
- Tree-model feature importance
- Persisted explanation records
- Clear separation between model explanation and causality