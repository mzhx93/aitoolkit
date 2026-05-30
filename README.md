# scnet-ocr-mcp

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Scnet OCR MCP Server，集成**通用 OCR** + **文档智能**两大能力，支持通过 MCP 协议调用。

## 功能

提供 4 个 MCP 工具：

| 工具 | 类型 | 说明 |
|------|------|------|
| `recognize_image_ocr` | 通用 OCR（同步） | 上传图片，同步返回识别结果。支持 56 种场景：通用文字、身份证、银行卡、营业执照、增值税发票等 |
| `submit_ocr_task` | 文档智能（异步） | 提交文档 URL，获取 task_id |
| `query_ocr_result` | 文档智能（异步） | 查询任务状态和结果下载链接 |
| `submit_and_wait_ocr` | 文档智能（同步） | 提交 + 自动轮询直到完成 |

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

### 通用 OCR（图片识别）
- **识别图片**: `POST /api/llm/v1/ocr/recognize` — multipart/form-data 上传
- 详见 [官方文档](https://www.scnet.cn/ac/openapi/doc/2.0/moduleapi/api/ocr.html)

### 文档智能（PDF/长文档）
- **提交任务**: `POST /api/llm/v1/ocrdoc/submit`
- **查询结果**: `POST /api/llm/v1/ocrdoc/result`
- 详见 [官方文档](https://www.scnet.cn/ac/openapi/doc/2.0/moduleapi/api/ocrdoc.html)

## 使用示例

```
# 通用 OCR — 识别单张图片
用户: 识别这张身份证 C:\Users\me\id_card.jpg
# → AI 调用 recognize_image_ocr(file_path="C:\\Users\\me\\id_card.jpg", ocr_type="ID_CARD")

# 文档智能 — 识别 PDF 文档
用户: 用 OCR 识别这个文档 https://example.com/doc.pdf
# → AI 调用 submit_and_wait_ocr(file_url="https://example.com/doc.pdf")
```

## 依赖

- Python >= 3.10
- mcp >= 1.0.0
- httpx >= 0.27.0

## License

MIT
