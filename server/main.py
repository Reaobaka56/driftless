from fastapi import FastAPI
from pydantic import BaseModel

from worker.queue import enqueue_scan

app = FastAPI(title="Driftless API")


class ScanRequest(BaseModel):
    repo_url: str
    vendor: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/scan", status_code=202)
def scan(req: ScanRequest):
    return {"job_id": enqueue_scan(req.repo_url, req.vendor)}
