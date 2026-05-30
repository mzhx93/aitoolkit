# Scnet OCR MCP Server

MCP server for [Scnet OCR Document Intelligence Service](https://www.scnet.cn/ac/openapi/doc/2.0/moduleapi/api/ocrdoc.html).

Async document OCR via Scnet's API: submit → poll → download.

## Tools

| Tool | Description |
|------|-------------|
| `ocr_submit_task` | Submit a document URL for OCR, returns task ID |
| `ocr_query_result` | Query task status/results by task IDs |
| `ocr_submit_and_wait` | Submit + auto-poll until complete or timeout |

## Quick Start

### npx (recommended)

```json
{
  "mcpServers": {
    "scnet-ocr": {
      "command": "npx",
      "args": ["-y", "scnet-ocr-mcp"],
      "env": { "SCNET_API_KEY": "your-api-key" }
    }
  }
}
```

Windows:

```json
{
  "mcpServers": {
    "scnet-ocr": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "scnet-ocr-mcp"],
      "env": { "SCNET_API_KEY": "your-api-key" }
    }
  }
}
```

### Global install

```bash
npm install -g scnet-ocr-mcp
```

```json
{
  "mcpServers": {
    "scnet-ocr": {
      "command": "scnet-ocr-mcp",
      "env": { "SCNET_API_KEY": "your-api-key" }
    }
  }
}
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SCNET_API_KEY` | Yes | - | Scnet API key |
| `SCNET_BASE_URL` | No | `https://api.scnet.cn/api/llm/v1/ocrdoc` | API base URL |
| `SCNET_POLL_INTERVAL` | No | `5` | Poll interval (seconds) |
| `SCNET_MAX_POLL_TIME` | No | `300` | Max wait for submit_and_wait |

## API Reference

Wraps [Scnet OCR Document Intelligence API](https://www.scnet.cn/ac/openapi/doc/2.0/moduleapi/api/ocrdoc.html).

### Task States

- `pending` - queued
- `running` - processing
- `succeeded` - done, results available
- `failed` - error occurred
- `unknown` - not found

## License

MIT
