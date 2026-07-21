from pathlib import Path
required = [
    "README.md","pyproject.toml","docker-compose.yml","src/finai/api/main.py",
    "src/finai/data/connectors/sec.py","src/finai/data/connectors/fred.py",
    "src/finai/models/risk/factor_model.py","src/finai/portfolio/optimizer.py",
    "apps/streamlit/app.py","r/forecasting/garch.R"
]
missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit(f"Missing required files: {missing}")
print("Structure validation passed.")
