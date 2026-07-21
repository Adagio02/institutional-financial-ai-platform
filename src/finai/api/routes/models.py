from fastapi import APIRouter
router = APIRouter(prefix="/models", tags=["models"])
@router.get("")
def models() -> list[dict[str, str]]:
    return [
        {"name": "elastic_net_alpha", "stage": "baseline"},
        {"name": "lightgbm_ranker", "stage": "candidate"},
        {"name": "factor_risk_model", "stage": "production_design"},
        {"name": "garch_volatility", "stage": "r_module"},
    ]
