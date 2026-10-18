from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="Exam Challenge MCP Server", docs_url=None, redoc_url=None)

EMAIL = "23f2001912@ds.study.iitm.ac.in"
PROTOCOL_VERSION = "2025-03-26"


def rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/mcp")
async def mcp_endpoint(request: Request) -> Response:
    # MCP Streamable HTTP: this stateless endpoint accepts JSON-RPC POSTs.
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(rpc_error(None, -32700, "Parse error"), status_code=400)

    if not isinstance(payload, dict):
        return JSONResponse(rpc_error(None, -32600, "Invalid Request"), status_code=400)

    method = payload.get("method")
    request_id = payload.get("id")
    params = payload.get("params") or {}

    # Notifications do not receive JSON-RPC responses.
    if method == "notifications/initialized" or (
        isinstance(method, str) and method.startswith("notifications/")
    ):
        return Response(status_code=202)

    if method == "initialize":
        requested_version = params.get("protocolVersion", PROTOCOL_VERSION)
        return JSONResponse(
            rpc_result(
                request_id,
                {
                    "protocolVersion": requested_version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "exam-challenge-mcp",
                        "version": "1.0.0",
                    },
                },
            ),
            headers={"MCP-Protocol-Version": str(requested_version)},
        )

    if method == "ping":
        return JSONResponse(rpc_result(request_id, {}))

    if method == "tools/list":
        return JSONResponse(
            rpc_result(
                request_id,
                {
                    "tools": [
                        {
                            "name": "solve_challenge",
                            "description": "Return the SHA-256 challenge answer for the current HTTP request headers.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": False,
                            },
                        }
                    ]
                },
            )
        )

    if method == "tools/call":
        name = params.get("name")
        if name != "solve_challenge":
            return JSONResponse(rpc_error(request_id, -32602, "Unknown tool"))
        challenge = request.headers.get("x-exam-challenge")
        if not challenge:
            return JSONResponse(
                rpc_result(
                    request_id,
                    {
                        "content": [
                            {"type": "text", "text": "Missing X-Exam-Challenge header"}
                        ],
                        "isError": True,
                    },
                )
            )
        answer = hashlib.sha256(f"{challenge}:{EMAIL}".encode("utf-8")).hexdigest()[:16]
        return JSONResponse(
            rpc_result(
                request_id,
                {"content": [{"type": "text", "text": answer}], "isError": False},
            )
        )

    return JSONResponse(rpc_error(request_id, -32601, "Method not found"))


# Some MCP clients use the root path as the configured endpoint.
@app.post("/")
async def mcp_root(request: Request) -> Response:
    return await mcp_endpoint(request)
