from prefect import flow


@flow(name="feature-build")
def run() -> dict[str, str]:
    return {"flow": "feature_build", "status": "configured"}


if __name__ == "__main__":
    print(run())
