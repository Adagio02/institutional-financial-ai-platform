from prefect import flow


@flow(name="rag-index")
def run() -> dict[str, str]:
    return {"flow": "rag_index", "status": "configured"}


if __name__ == "__main__":
    print(run())
