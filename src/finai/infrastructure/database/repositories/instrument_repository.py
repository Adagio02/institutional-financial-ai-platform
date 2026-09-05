from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from finai.domain.market_data.entities import Instrument
from finai.domain.market_data.enums import AssetClass
from finai.domain.market_data.validation import (
    normalize_symbol,
    validate_instrument,
)
from finai.infrastructure.database.models.instrument import InstrumentModel
from finai.infrastructure.database.repositories.exceptions import (
    InstrumentAlreadyExistsError,
    InstrumentNotFoundError,
)


class InstrumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, instrument: Instrument) -> Instrument:
        validate_instrument(instrument)

        model = InstrumentModel(
            symbol=normalize_symbol(instrument.symbol),
            name=instrument.name.strip(),
            asset_class=instrument.asset_class.value,
            exchange=instrument.exchange.strip().upper(),
            currency=instrument.currency.strip().upper(),
            active=instrument.active,
        )

        self._session.add(model)

        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()

            raise InstrumentAlreadyExistsError(
                f"Instrument '{model.symbol}' already exists."
            ) from error

        self._session.refresh(model)

        return self._to_entity(model)

    def get_by_symbol(self, symbol: str) -> Instrument:
        normalized_symbol = normalize_symbol(symbol)

        statement = select(InstrumentModel).where(InstrumentModel.symbol == normalized_symbol)

        model = self._session.scalar(statement)

        if model is None:
            raise InstrumentNotFoundError(f"Instrument '{normalized_symbol}' was not found.")

        return self._to_entity(model)

    def get_model_by_symbol(self, symbol: str) -> InstrumentModel:
        normalized_symbol = normalize_symbol(symbol)

        statement = select(InstrumentModel).where(InstrumentModel.symbol == normalized_symbol)

        model = self._session.scalar(statement)

        if model is None:
            raise InstrumentNotFoundError(f"Instrument '{normalized_symbol}' was not found.")

        return model

    def list_all(
        self,
        *,
        active_only: bool = True,
    ) -> list[Instrument]:
        statement = select(InstrumentModel).order_by(InstrumentModel.symbol)

        if active_only:
            statement = statement.where(InstrumentModel.active.is_(True))

        models = self._session.scalars(statement).all()

        return [self._to_entity(model) for model in models]

    @staticmethod
    def _to_entity(model: InstrumentModel) -> Instrument:
        return Instrument(
            instrument_id=model.id,
            symbol=model.symbol,
            name=model.name,
            asset_class=AssetClass(model.asset_class),
            exchange=model.exchange,
            currency=model.currency,
            active=model.active,
        )
