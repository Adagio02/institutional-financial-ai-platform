from prefect import flow


@flow(name="backtest")
def run() -> dict[str, str]:
    return {"flow": "backtest", "status": "configured"}


if __name__ == "__main__":
    print(run())
