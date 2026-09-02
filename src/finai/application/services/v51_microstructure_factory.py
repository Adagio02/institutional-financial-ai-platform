import os

from finai.application.services.v51_microstructure_service import V51MicrostructureService


def build_v51_microstructure_service() -> V51MicrostructureService:
    return V51MicrostructureService(
        quote_path=os.getenv("FINAI_V51_QUOTE_PATH", "data/research/quotes")
    )

