# eShopCo Regional Latency API

A serverless FastAPI endpoint that summarizes the supplied storefront telemetry by region.

## Endpoint
- `POST /api/latency`
- `GET /health`
- CORS allows any origin, POST/OPTIONS methods, and all headers.

### Request
```json
{"regions":["amer","apac"],"threshold_ms":185}
```

### Response shape
```json
{
  "amer": {
    "avg_latency": 187.58,
    "p95_latency": 228.16,
    "avg_uptime": 98.334,
    "breaches": 8
  }
}
```
The numbers above are illustrative only; use the deployed endpoint for actual results. Latency percentile uses NumPy's default linear percentile method. A breach is a record with latency strictly greater than the requested threshold.

## Deploy on Vercel
1. Import this repository into Vercel.
2. Set the project root to the repository root.
3. Deploy. No secrets or environment variables are required.
4. Test with:
```bash
curl -X POST 'https://YOUR-DEPLOYMENT.vercel.app/api/latency' \
  -H 'Content-Type: application/json' \
  -d '{"regions":["amer","apac"],"threshold_ms":185}'
```

The sample data is stored in `data/telemetry.json` and is loaded from the repository at runtime.
