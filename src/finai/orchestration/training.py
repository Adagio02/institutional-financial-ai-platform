from prefect import flow


@flow(name="training")
def run() -> dict[str, str]:
    return {"flow": "training", "status": "configured"}


if __name__ == "__main__":
    print(run())
