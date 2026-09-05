from prefect import flow


@flow(name="model-monitoring")
def run() -> dict[str, str]:
    return {"flow": "model_monitoring", "status": "configured"}


if __name__ == "__main__":
    print(run())
