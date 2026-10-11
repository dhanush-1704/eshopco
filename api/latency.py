from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="eShopCo Regional Latency Metrics", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.json"


class MetricsRequest(BaseModel):
    regions: list[str] = Field(min_length=1)
    threshold_ms: float = Field(default=180, ge=0)


def load_telemetry() -> list[dict[str, Any]]:
    try:
        with DATA_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Unable to load telemetry data") from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/latency")
def regional_metrics(payload: MetricsRequest):
    records = load_telemetry()
    result: dict[str, dict[str, float | int]] = {}
    for region in payload.regions:
        subset = [r for r in records if r.get("region") == region]
        if not subset:
            raise HTTPException(status_code=404, detail=f"No telemetry found for region '{region}'")
        latencies = np.asarray([float(r["latency_ms"]) for r in subset], dtype=float)
        uptimes = np.asarray([float(r["uptime_pct"]) for r in subset], dtype=float)
        result[region] = {
            "avg_latency": round(float(np.mean(latencies)), 3),
            "p95_latency": round(float(np.percentile(latencies, 95)), 3),
            "avg_uptime": round(float(np.mean(uptimes)), 3),
            "breaches": int(np.count_nonzero(latencies > payload.threshold_ms)),
        }
    return result
