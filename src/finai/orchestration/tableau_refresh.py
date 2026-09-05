from prefect import flow


@flow(name="tableau-refresh")
def run() -> dict[str, str]:
    return {"flow": "tableau_refresh", "status": "configured"}


if __name__ == "__main__":
    print(run())
