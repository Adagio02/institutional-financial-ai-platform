from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass(frozen=True, slots=True)
class V47Instrument:
    symbol: str
    name: str
    asset_class: str
    exchange: str
    sector: str
    benchmark: str
    enabled: bool = True

@dataclass(frozen=True, slots=True)
class V47Universe:
    instruments: tuple[V47Instrument, ...]
    benchmarks: tuple[str, ...]
    sector_etfs: dict[str, str]

    @property
    def symbols(self) -> list[str]:
        return [x.symbol for x in self.instruments if x.enabled]

    @property
    def equity_symbols(self) -> list[str]:
        return [x.symbol for x in self.instruments if x.enabled and x.sector != "ETF"]

    def by_symbol(self) -> dict[str, V47Instrument]:
        return {x.symbol: x for x in self.instruments}

def load_v47_universe(path: str | Path) -> V47Universe:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    instruments = tuple(
        V47Instrument(
            symbol=str(x["symbol"]).strip().upper(),
            name=str(x.get("name", x["symbol"])).strip(),
            asset_class=str(x.get("asset_class", "equity")).strip().lower(),
            exchange=str(x.get("exchange", "US")).strip().upper(),
            sector=str(x.get("sector", "Unknown")).strip(),
            benchmark=str(x.get("benchmark", "SPY")).strip().upper(),
            enabled=bool(x.get("enabled", True)),
        )
        for x in payload["instruments"]
    )
    symbols = [x.symbol for x in instruments]
    if len(symbols) != len(set(symbols)):
        raise ValueError("V4.7 universe contains duplicate symbols.")
    return V47Universe(
        instruments=instruments,
        benchmarks=tuple(str(x).upper() for x in payload.get("benchmarks", [])),
        sector_etfs={str(k): str(v).upper() for k, v in payload.get("sector_etfs", {}).items()},
    )
