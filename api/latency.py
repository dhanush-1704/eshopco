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


# Stateless Streamable HTTP MCP endpoint for the exam challenge.
import hashlib
from fastapi import Request
from fastapi.responses import JSONResponse, Response

EXAM_EMAIL = "23f2001912@ds.study.iitm.ac.in"
MCP_PROTOCOL_VERSION = "2025-03-26"


@app.post("/api/mcp")
async def mcp_endpoint(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )
    if not isinstance(payload, dict):
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}},
            status_code=400,
        )

    method = payload.get("method")
    request_id = payload.get("id")
    params = payload.get("params") or {}

    if isinstance(method, str) and method.startswith("notifications/"):
        return Response(status_code=202)

    if method == "initialize":
        version = params.get("protocolVersion", MCP_PROTOCOL_VERSION)
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "exam-challenge-mcp", "version": "1.0.0"},
                },
            },
            headers={"MCP-Protocol-Version": str(version)},
        )

    if method == "ping":
        return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": {}})

    if method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [{
                    "name": "solve_challenge",
                    "description": "Return the SHA-256 answer for the challenge in this request's HTTP headers.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }]
            }
        })

    if method == "tools/call":
        if params.get("name") != "solve_challenge":
            return JSONResponse({
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32602, "message": "Unknown tool"}
            })
        challenge = request.headers.get("x-exam-challenge")
        if not challenge:
            return JSONResponse({
                "jsonrpc": "2.0", "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": "Missing X-Exam-Challenge header"}],
                    "isError": True
                }
            })
        digest = hashlib.sha256(f"{challenge}:{EXAM_EMAIL}".encode("utf-8")).hexdigest()[:16]
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": digest}], "isError": False}
        })

    return JSONResponse({
        "jsonrpc": "2.0", "id": request_id,
        "error": {"code": -32601, "message": "Method not found"}
    })
