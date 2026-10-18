# Exam Challenge MCP Server

This repository includes a stateless MCP JSON-RPC endpoint at `POST /api/mcp` exposing exactly one tool, `solve_challenge`.

Each tool call reads `X-Exam-Challenge` from the current HTTP request headers and returns the first 16 lowercase hex characters of SHA-256(`challenge:23f2001912@ds.study.iitm.ac.in`). The timestamp and signature headers are not required because signature verification is optional.

MCP methods supported: `initialize`, `notifications/initialized`, `tools/list`, `tools/call`, and `ping`.
