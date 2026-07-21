from abc import ABC, abstractmethod
import polars as pl

class DataConnector(ABC):
    @abstractmethod
    def fetch(self, **kwargs) -> pl.DataFrame:
        raise NotImplementedError
