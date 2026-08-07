from uuid import UUID

from sqlalchemy.orm import Session

from pathlib import Path

from finai.domain.modeling.enums import ModelStage
from finai.infrastructure.database.repositories.evaluation_result_repository import (
    EvaluationResultRepository,
)
from finai.infrastructure.database.repositories.model_artifact_repository import (
    ModelArtifactRepository,
)
from finai.infrastructure.database.repositories.model_card_repository import (
    ModelCardRepository,
)
from finai.infrastructure.database.repositories.training_run_repository import (
    TrainingRunRepository,
)
from finai.infrastructure.prediction.artifact_verifier import (
    verify_artifact_hash,
)


class ModelGovernanceService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._model_repository = ModelArtifactRepository(session)
        self._training_repository = TrainingRunRepository(session)
        self._evaluation_repository = EvaluationResultRepository(session)
        self._model_card_repository = ModelCardRepository(session)

    def create_model_card(
        self,
        *,
        model_id: UUID,
        summary: str,
        intended_use: str,
        limitations: str,
    ):
        model = self._require_model(model_id)

        training_run = self._training_repository.get_by_id(model.training_run_id)

        if training_run is None:
            raise LookupError("Training run for model was not found.")

        evaluations = self._evaluation_repository.list_for_run(training_run.id)

        evaluation_summary = {
            f"fold_{result.fold_number}": result.metrics for result in evaluations
        }

        return self._model_card_repository.create(
            model_id=model.id,
            summary=summary,
            intended_use=intended_use,
            limitations=limitations,
            evaluation_summary=evaluation_summary,
            governance_metadata={
                "artifact_hash": model.artifact_hash,
                "training_run_id": str(training_run.id),
                "dataset_id": str(training_run.dataset_id),
            },
        )

    def evaluate_for_production(
        self,
        *,
        model_id: UUID,
        minimum_accuracy: float = 0.50,
        minimum_r_squared: float = -1.0,
    ) -> dict:
        model = self._require_model(model_id)

        if model.stage != ModelStage.STAGING.value:
            raise ValueError("Only staging models can be evaluated for production.")

        verify_artifact_hash(
            path=Path(model.artifact_uri),
            expected_hash=model.artifact_hash,
        )

        model_card = self._model_card_repository.get_for_model(model.id)

        if model_card is None:
            raise ValueError("A model card is required before production approval.")

        training_run = self._training_repository.get_by_id(model.training_run_id)

        if training_run is None:
            raise LookupError("Training run was not found.")

        if training_run.status != "completed":
            raise ValueError("The training run is not completed.")

        evaluations = self._evaluation_repository.list_for_run(training_run.id)

        if not evaluations:
            raise ValueError("The model does not have evaluation results.")

        aggregate = self._aggregate_metrics(evaluations)

        prediction_task = training_run.prediction_task

        if prediction_task == "classification":
            accuracy = aggregate.get("accuracy")

            if accuracy is None:
                raise ValueError("Classification evaluation is missing accuracy.")

            if accuracy < minimum_accuracy:
                raise ValueError("Model accuracy is below the production threshold.")

        elif prediction_task == "regression":
            r_squared = aggregate.get("r_squared")

            if r_squared is None:
                raise ValueError("Regression evaluation is missing r_squared.")

            if r_squared < minimum_r_squared:
                raise ValueError("Model r_squared is below the production threshold.")

        else:
            raise ValueError("Unsupported prediction task.")

        return {
            "approved": True,
            "metrics": aggregate,
            "artifact_verified": True,
            "model_card_present": True,
        }

    def promote_to_production(
        self,
        *,
        model_id: UUID,
        minimum_accuracy: float = 0.50,
        minimum_r_squared: float = -1.0,
    ):
        self.evaluate_for_production(
            model_id=model_id,
            minimum_accuracy=minimum_accuracy,
            minimum_r_squared=minimum_r_squared,
        )

        model = self._require_model(model_id)

        return self._model_repository.update_stage(
            model,
            stage=ModelStage.PRODUCTION.value,
        )

    def _require_model(self, model_id: UUID):
        model = self._model_repository.get_by_id(model_id)

        if model is None:
            raise LookupError(f"Model not found: {model_id}")

        return model

    @staticmethod
    def _aggregate_metrics(
        evaluations,
    ) -> dict[str, float]:
        metric_names = {
            metric_name for evaluation in evaluations for metric_name in evaluation.metrics
        }

        return {
            metric_name: sum(
                evaluation.metrics[metric_name]
                for evaluation in evaluations
                if metric_name in evaluation.metrics
            )
            / sum(1 for evaluation in evaluations if metric_name in evaluation.metrics)
            for metric_name in metric_names
        }
