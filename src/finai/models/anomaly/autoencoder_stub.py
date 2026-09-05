"""Model component: anomaly.autoencoder_stub."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "autoencoder_stub"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {
        "group": "anomaly",
        "component": "autoencoder_stub",
        "status": "implementation scaffold",
    }
