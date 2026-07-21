from prefect import flow

@flow(name="inference")
def run() -> dict[str, str]:
    return {"flow": "inference", "status": "configured"}

if __name__ == "__main__":
    print(run())
