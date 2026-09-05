import json

from finai.application.services.v482_ranking_factory import build_v482_ranking_service
from finai.core.config import get_settings


result = build_v482_ranking_service(settings=get_settings()).run()
print(json.dumps({
    "version": result["version"],
    "stage": result["stage"],
    "model_names": result["model_names"],
    "target_columns": result["target_columns"],
    "out_of_sample_prediction_rows": result["out_of_sample_prediction_rows"],
    "prediction_path": result["prediction_path"],
    "model_path": result["model_path"],
    "next_step": result["next_step"],
}, indent=2, default=str))
