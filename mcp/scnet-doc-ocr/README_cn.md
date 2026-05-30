# Scnet OCR MCP Server

基于 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 的 [Scnet OCR 文档智能服务](https://www.scnet.cn/ac/openapi/doc/2.0/moduleapi/api/ocrdoc.html) 服务端。

提供异步文档 OCR 能力，支持 提交 → 轮询 → 下载 的标准处理流程。

## 工具列表

| 工具 | 说明 |
|------|------|
| `ocr_submit_task` | 提交文档 URL 进行 OCR 识别，返回任务 ID |
| `ocr_query_result` | 按任务 ID 查询状态与结果 |
| `ocr_submit_and_wait` | 提交并自动轮询，直到完成或超时 |

## 环境要求

- Node.js >= 18
- Scnet API Key（从 [Scnet 控制台](https://www.scnet.cn/) 获取）

## 快速开始

### npx 方式（推荐）

```json
{
  "mcpServers": {
    "scnet-ocr": {
      "command": "npx",
      "args": ["-y", "scnet-ocr-mcp"],
      "env": {
        "SCNET_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Windows 需用 `cmd /c` 包装：

```json
{
  "mcpServers": {
    "scnet-ocr": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "scnet-ocr-mcp"],
      "env": {
        "SCNET_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### 本地安装 + 运行

```bash
npm install -g scnet-ocr-mcp
```

```json
{
  "mcpServers": {
    "scnet-ocr": {
      "command": "scnet-ocr-mcp",
      "env": { "SCNET_API_KEY": "your-api-key-here" }
    }
  }
}
```

## 配置说明

| 环境变量 | 必填 | 默认值 | 说明 |
|----------|------|--------|------|
| `SCNET_API_KEY` | 是 | - | Scnet API 密钥 |
| `SCNET_BASE_URL` | 否 | `https://api.scnet.cn/api/llm/v1/ocrdoc` | API 基础地址 |
| `SCNET_POLL_INTERVAL` | 否 | `5` | 轮询间隔（秒） |
| `SCNET_MAX_POLL_TIME` | 否 | `300` | submit_and_wait 最大等待时间（秒） |

## API 说明

本 MCP Server 封装了 [Scnet OCR 文档智能服务 API](https://www.scnet.cn/ac/openapi/doc/2.0/moduleapi/api/ocrdoc.html)。

### 处理流程

1. **提交任务**：POST `/submit`，传入 `file_url` → 获取 `task_id`
2. **查询状态**：POST `/result`，传入 `task_ids` → 查看处理状态
3. **获取结果**：状态为 `succeeded` 时，结果中包含文件下载地址

### 任务状态说明

| 状态 | 含义 |
|------|------|
| `pending` | 任务已提交，等待处理 |
| `running` | 任务处理中 |
| `succeeded` | 处理成功，可下载结果 |
| `failed` | 处理失败 |
| `unknown` | 任务不存在或未知状态 |

## 许可证

MIT
