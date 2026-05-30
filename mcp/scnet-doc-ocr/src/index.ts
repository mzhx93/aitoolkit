#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// 从环境变量读取配置
const API_KEY = process.env.SCNET_API_KEY || "";
const BASE_URL = process.env.SCNET_BASE_URL || "https://api.scnet.cn/api/llm/v1/ocrdoc";
const POLL_INTERVAL = parseInt(process.env.SCNET_POLL_INTERVAL || "5", 10);
const MAX_POLL_TIME = parseInt(process.env.SCNET_MAX_POLL_TIME || "300", 10);

// 创建 MCP Server 实例
const server = new McpServer({
  name: "scnet-ocr-mcp",
  version: "0.1.0",
}, {
  capabilities: { tools: {} },
});

// 向 Scnet OCR API 发起 HTTP 请求
async function request(method: string, path: string, body?: Record<string, unknown>): Promise<unknown> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${API_KEY}`,
    "Content-Type": "application/json",
  };

  const options: RequestInit = { method, headers };
  if (body) {
    options.body = JSON.stringify(body);
  }

  const resp = await fetch(url, options);
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
  }
  return resp.json();
}

// 注册工具：提交 OCR 识别任务
server.tool(
  "ocr_submit_task",
  "提交文档进行 OCR 识别。需提供文档的公网可访问 URL，返回 task_id 用于后续查询。",
  {
    file_url: z.string().describe("待识别文档的公网可访问下载地址"),
    ocr_type: z.string().default("DOC_PARING").describe("识别类别，目前仅支持 DOC_PARING"),
  },
  async ({ file_url, ocr_type }) => {
    const body: Record<string, string> = { file_url };
    if (ocr_type) body.ocr_type = ocr_type;

    const result = await request("POST", "/submit", body);
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }
);

// 注册工具：查询 OCR 任务状态与结果
server.tool(
  "ocr_query_result",
  "根据任务 ID 查询 OCR 任务的状态和结果。返回任务状态、提交时间、结束时间，成功时返回结果文件下载地址。",
  {
    task_ids: z.array(z.string()).describe("要查询的任务 ID 列表"),
  },
  async ({ task_ids }) => {
    const result = await request("POST", "/result", { task_ids });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }
);

// 注册工具：提交并轮询直到完成
server.tool(
  "ocr_submit_and_wait",
  "提交文档进行 OCR 识别并等待结果。便捷方法，合并了提交和轮询操作。",
  {
    file_url: z.string().describe("待识别文档的公网可访问下载地址"),
    ocr_type: z.string().default("DOC_PARING").describe("识别类别"),
    poll_interval: z.number().default(POLL_INTERVAL).describe(`轮询间隔，单位秒（默认: ${POLL_INTERVAL}）`),
    max_wait: z.number().default(MAX_POLL_TIME).describe(`最大等待时间，单位秒（默认: ${MAX_POLL_TIME}）`),
  },
  async ({ file_url, ocr_type, poll_interval, max_wait }) => {
    // 第一步：提交任务
    const submitBody: Record<string, string> = { file_url };
    if (ocr_type) submitBody.ocr_type = ocr_type;

    const submitResult = await request("POST", "/submit", submitBody) as Record<string, unknown>;
    const data = (submitResult.data as Record<string, unknown>) || {};
    const output = (data.output as Record<string, unknown>) || {};
    const task_id = (output.task_id as string) || "";

    if (!task_id) {
      return { content: [{ type: "text", text: `提交失败，未能获取 task_id: ${JSON.stringify(submitResult)}` }] };
    }

    // 第二步：轮询等待结果
    const statusTexts: string[] = [];
    const start = Date.now();

    while (Date.now() - start < max_wait * 1000) {
      const queryResult = await request("POST", "/result", { task_ids: [task_id] }) as Record<string, unknown>;
      const taskData = (queryResult.data as Array<Record<string, unknown>>) || [];

      if (taskData.length > 0) {
        const itemOutput = (taskData[0].output as Record<string, unknown>) || {};
        const status = (itemOutput.task_status as string) || "unknown";

        if (status === "succeeded") {
          statusTexts.push(`[成功] task_id=${task_id}`);
          statusTexts.push(JSON.stringify(queryResult, null, 2));
          return { content: [{ type: "text", text: statusTexts.join("\n") }] };
        } else if (status === "failed") {
          statusTexts.push(`[失败] task_id=${task_id}`);
          statusTexts.push(JSON.stringify(queryResult, null, 2));
          return { content: [{ type: "text", text: statusTexts.join("\n") }] };
        } else {
          statusTexts.push(`[${status}] task_id=${task_id}, 已等待${Math.floor((Date.now() - start) / 1000)}秒`);
        }
      }

      await new Promise((resolve) => setTimeout(resolve, poll_interval * 1000));
    }

    statusTexts.push(`[超时] task_id=${task_id} 在 ${max_wait} 秒内未完成，请稍后使用 ocr_query_result 查询。`);
    return { content: [{ type: "text", text: statusTexts.join("\n") }] };
  }
);

// 启动 MCP stdio 服务
async function main() {
  if (!API_KEY) {
    console.error("错误: 未设置 SCNET_API_KEY 环境变量。");
    process.exit(1);
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("服务启动失败:", err);
  process.exit(1);
});
