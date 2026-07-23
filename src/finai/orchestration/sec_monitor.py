from prefect import flow


@flow(name="sec-monitor")
def run() -> dict[str, str]:
    return {"flow": "sec_monitor", "status": "configured"}


if __name__ == "__main__":
    print(run())
