from prefect import flow

@flow(name="daily-market")
def run() -> dict[str, str]:
    return {"flow": "daily_market", "status": "configured"}

if __name__ == "__main__":
    print(run())
