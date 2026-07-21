from prefect import flow

@flow(name="quality-checks")
def run() -> dict[str, str]:
    return {"flow": "quality_checks", "status": "configured"}

if __name__ == "__main__":
    print(run())
