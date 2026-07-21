from prefect import flow

@flow(name="weekly-research")
def run() -> dict[str, str]:
    return {"flow": "weekly_research", "status": "configured"}

if __name__ == "__main__":
    print(run())
