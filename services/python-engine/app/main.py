import os

from fastapi import FastAPI


app = FastAPI(title="QuantumValue Engine", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {
        "service": "engine-py",
        "status": "ok",
        "database_url": os.getenv("DATABASE_URL", "not-configured"),
    }
