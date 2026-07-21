from prefect import flow

@flow(name="daily-macro")
def run() -> dict[str, str]:
    return {"flow": "daily_macro", "status": "configured"}

if __name__ == "__main__":
    print(run())
