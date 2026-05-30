# scnet-ocr-mcp

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Scnet OCR 文档智能服务 MCP Server，支持通过 Model Context Protocol 调用 Scnet 平台的 OCR 文档识别 API。

## 功能

提供 3 个 MCP 工具：

| 工具 | 说明 |
|------|------|
| `submit_ocr_task` | 提交文档 URL，获取 task_id（异步） |
| `query_ocr_result` | 传入 task_ids 列表，查询任务状态和结果下载链接 |
| `submit_and_wait_ocr` | 提交任务并自动轮询直到完成（同步体验） |

## 快速开始

### 1. 获取 API Key

登录 [Scnet 平台](https://www.scnet.cn)，在 API Key 管理页面创建密钥。

### 2. 配置 opencode（推荐 uvx，零安装）

复制 `opencode.example.json` → `opencode.json`，填入你的 API Key：

```json
{
  "mcpServers": {
    "scnet-doc-ocr": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/mzhx93/aitoolkit.git@scnet-doc-ocr", "scnet-ocr-mcp"],
      "env": {
        "SCNET_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

`uvx` 会自动拉取仓库、安装依赖并启动服务，无需手动 clone 或 pip install。

### 手动安装（可选）

```bash
pip install git+https://github.com/mzhx93/aitoolkit.git@scnet-doc-ocr
```

然后在 opencode.json 中：

```json
{
  "mcpServers": {
    "scnet-doc-ocr": {
      "command": "python",
      "args": ["-m", "scnet_ocr_mcp.server"],
      "env": {
        "SCNET_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `SCNET_API_KEY` | 是 | - | Scnet 平台 API Key |
| `SCNET_BASE_URL` | 否 | `https://api.scnet.cn/api/llm/v1/ocrdoc` | API 基础地址 |
| `POLL_INTERVAL` | 否 | `5` | 轮询间隔（秒） |
| `MAX_POLL_ATTEMPTS` | 否 | `60` | 最大轮询次数 |

## API 接口

基于 Scnet OCR 文档智能服务：

- **提交任务**: `POST /api/llm/v1/ocrdoc/submit`
- **查询结果**: `POST /api/llm/v1/ocrdoc/result`

详见 [官方文档](https://www.scnet.cn/ac/openapi/doc/2.0/moduleapi/api/ocrdoc.html)。

## 使用示例

```
# 提交 OCR 任务
用户: 用 OCR 识别这个文档 https://example.com/doc.pdf

# AI 自动调用 submit_ocr_task，返回 task_id
# 然后调用 query_ocr_result 查询结果
# 获取到的 results[] 中包含识别结果 JSON 的下载地址
```

## 依赖

- Python >= 3.10
- mcp >= 1.0.0
- httpx >= 0.27.0

## License

MIT
