import asyncio
import os
from typing import Any

import httpx
from mcp.server import FastMCP

mcp = FastMCP("scnet-ocr-doc")


def _get_config() -> dict[str, Any]:
    api_key = os.getenv("SCNET_API_KEY", "")
    base_url = os.getenv("SCNET_BASE_URL", "https://api.scnet.cn/api/llm/v1/ocrdoc")
    poll_interval = int(os.getenv("POLL_INTERVAL", "5"))
    max_poll_attempts = int(os.getenv("MAX_POLL_ATTEMPTS", "60"))
    return {
        "api_key": api_key,
        "submit_url": f"{base_url}/submit",
        "result_url": f"{base_url}/result",
        "poll_interval": poll_interval,
        "max_poll_attempts": max_poll_attempts,
    }


def _get_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _check_api_key(api_key: str) -> None:
    if not api_key:
        raise ValueError(
            "SCNET_API_KEY 未设置。请在 MCP 客户端配置中设置 env.SCNET_API_KEY。"
        )


@mcp.tool()
async def submit_ocr_task(
    file_url: str,
    ocr_type: str = "DOC_PARING",
) -> dict[str, Any]:
    """提交文档进行 OCR 识别任务。

    将待处理的文件 URL 提交到 Scnet OCR 文档智能服务，获取任务 ID 用于后续查询。

    Args:
        file_url: 待处理文件的公网可访问下载地址。需要先通过文件上传接口获取。
        ocr_type: 识别类别，目前仅支持 DOC_PARING（文档解析）。
    """
    cfg = _get_config()
    _check_api_key(cfg["api_key"])
    payload = {"file_url": file_url, "ocr_type": ocr_type}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            cfg["submit_url"], json=payload, headers=_get_headers(cfg["api_key"])
        )
        data = resp.json()

    if resp.status_code >= 400:
        return {"error": True, "status_code": resp.status_code, "detail": data}

    return {
        "success": True,
        "task_id": data.get("data", {}).get("output", {}).get("task_id", ""),
        "task_status": data.get("data", {}).get("output", {}).get("task_status", ""),
        "request_id": data.get("data", {}).get("request_id", ""),
        "raw": data,
    }


@mcp.tool()
async def query_ocr_result(task_ids: list[str]) -> dict[str, Any]:
    """查询 OCR 识别任务的状态和结果。

    根据任务 ID 列表查询对应任务的处理状态，成功时会返回识别结果文件的下载地址。

    Args:
        task_ids: 任务 ID 列表，可以一次查询多个任务。
    """
    cfg = _get_config()
    _check_api_key(cfg["api_key"])
    payload = {"task_ids": task_ids}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            cfg["result_url"], json=payload, headers=_get_headers(cfg["api_key"])
        )
        data = resp.json()

    if resp.status_code >= 400:
        return {"error": True, "status_code": resp.status_code, "detail": data}

    results = []
    for item in data.get("data", []):
        output = item.get("output", {})
        entry = {
            "task_id": output.get("task_id", ""),
            "task_status": output.get("task_status", ""),
            "submit_time": output.get("submit_time", ""),
            "end_time": output.get("end_time"),
            "results": output.get("results", []),
            "error_code": output.get("error_code"),
            "error_message": output.get("error_message"),
            "usage": item.get("usage", {}),
            "request_id": item.get("request_id", ""),
        }
        results.append(entry)

    return {"success": True, "tasks": results, "raw": data}


@mcp.tool()
async def submit_and_wait_ocr(
    file_url: str,
    ocr_type: str = "DOC_PARING",
) -> dict[str, Any]:
    """提交 OCR 任务并轮询等待直到完成。

    一步完成提交和等待结果，适合处理单个文档。

    Args:
        file_url: 待处理文件的公网可访问下载地址。
        ocr_type: 识别类别，目前仅支持 DOC_PARING。
    """
    cfg = _get_config()
    _check_api_key(cfg["api_key"])
    headers = _get_headers(cfg["api_key"])

    async with httpx.AsyncClient(timeout=30.0) as client:
        submit_payload = {"file_url": file_url, "ocr_type": ocr_type}
        resp = await client.post(cfg["submit_url"], json=submit_payload, headers=headers)
        submit_data = resp.json()

        if resp.status_code >= 400:
            return {"error": True, "stage": "submit", "detail": submit_data}

        task_id = submit_data.get("data", {}).get("output", {}).get("task_id", "")
        if not task_id:
            return {"error": True, "stage": "submit", "detail": "未获取到 task_id", "raw": submit_data}

        for attempt in range(cfg["max_poll_attempts"]):
            await asyncio.sleep(cfg["poll_interval"])

            query_payload = {"task_ids": [task_id]}
            resp = await client.post(cfg["result_url"], json=query_payload, headers=headers)
            query_data = resp.json()

            if resp.status_code >= 400:
                return {
                    "error": True,
                    "stage": "query",
                    "attempt": attempt + 1,
                    "detail": query_data,
                }

            task_list = query_data.get("data", [])
            if not task_list:
                continue

            output = task_list[0].get("output", {})
            status = output.get("task_status", "")

            if status == "succeeded":
                return {
                    "success": True,
                    "task_id": task_id,
                    "task_status": status,
                    "submit_time": output.get("submit_time", ""),
                    "end_time": output.get("end_time", ""),
                    "results": output.get("results", []),
                    "poll_attempts": attempt + 1,
                    "raw": query_data,
                }

            if status == "failed":
                return {
                    "success": False,
                    "task_id": task_id,
                    "task_status": status,
                    "error_code": output.get("error_code", ""),
                    "error_message": output.get("error_message", ""),
                    "raw": query_data,
                }

        return {
            "success": False,
            "task_id": task_id,
            "task_status": "timeout",
            "message": f"轮询超过最大尝试次数 ({cfg['max_poll_attempts']})，任务仍未完成",
            "poll_attempts": cfg["max_poll_attempts"],
        }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
