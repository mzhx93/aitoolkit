import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server import FastMCP

mcp = FastMCP("scnet-ocr")


def _get_config() -> dict[str, Any]:
    api_key = os.getenv("SCNET_API_KEY", "")
    base_url = os.getenv("SCNET_BASE_URL", "https://api.scnet.cn/api/llm/v1/ocrdoc")
    ocr_base_url = os.getenv(
        "SCNET_OCR_BASE_URL", "https://api.scnet.cn/api/llm/v1/ocr/recognize"
    )
    poll_interval = int(os.getenv("POLL_INTERVAL", "5"))
    max_poll_attempts = int(os.getenv("MAX_POLL_ATTEMPTS", "60"))
    return {
        "api_key": api_key,
        "submit_url": f"{base_url}/submit",
        "result_url": f"{base_url}/result",
        "ocr_recognize_url": ocr_base_url,
        "poll_interval": poll_interval,
        "max_poll_attempts": max_poll_attempts,
    }


def _get_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _get_form_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


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


OCR_TYPES = [
    "GENERAL", "BILL_MIXING_AND_IDENTIFICATION", "SEAL_CHARACTER_RECOGNITION",
    "ID_CARD", "BANK_CARD", "SOCIAL_SECURITY_CARD", "HOUSEHOLD_REGISTER",
    "BIRTH_CERTIFICATE", "HK_MACAU_PASS", "TAIWAN_PASS", "TAIWAN_MAINLAND_PASS",
    "HK_MAINLAND_PASS", "HONG_KONG_IDENTITY_CARD", "PERMANENT_RESIDENCE_ID_CARD_FOR",
    "MARRIAGE_CERTIFICATE", "REAL_ESTATE_OWNERSHIP_CERTIFICAT",
    "FRONT_PAGE_OF_MOTOR_VEHICLE_DRIV", "SECOND_SHEET_OF_MOTOR_VEHICLE_DR",
    "MOTOR_VEHICLE_DRIVING_LICENSE", "MOTOR_VEHICLE_DRIVING_LICENSE_SU",
    "CHINESE_PASSPORT", "ACADEMIC_CERTIFICATE", "ONLINE_VERIFICATION_REPORT_OF_HE",
    "DIPLOMA", "BUSINESS_LICENSE", "SOCIAL_ORG_REG", "TRADE_UNION_REG",
    "PRIVATE_NON_ENTERPRISE_REG", "INSTITUTION_LEGAL_REG", "UNIFIED_SOCIAL_CREDIT_REG",
    "UNIFIED_IDENTIFICATION_OF_FINANC", "VAT_INVOICE", "VAT_ROLL_INVOICE",
    "TAXI_INVOICE", "TRAIN_TICKET", "AIRPORT_TICKET", "VEHICLE_SALE_INVOICE",
    "QUOTA_INVOICE", "TOLL_INVOICE", "MEDICAL_INVOICE", "TAX_CERTIFICATE",
    "SHIP_TICKET", "NON_TAX_BILL", "GENERAL_MACHINE_INVOICE", "BUS_TICKET",
    "BANK_DRAFT", "BANK_ACCEPTANCE_BILL", "ELECTRONIC_BANK_ACCEPTANCE_BILL",
    "COMMERCIAL_ACCEPTANCE_BILL", "ELECTRONIC_COMMERCIAL_ACCEPTANCE",
    "BANK_CHECK", "BANK_RECEIPT", "DEPOSIT_SLIP", "TELEGRAPHIC_TRANSFER_VOUCHER",
    "WITHDRAWAL_VOUCHER", "MOBILE_PAYMENT_BILL",
]


@mcp.tool()
async def recognize_image_ocr(
    file_path: str = "",
    file_url: str = "",
    ocr_type: str = "GENERAL",
) -> dict[str, Any]:
    """通用 OCR 图片识别，同步返回结果。

    支持 56 种识别场景：
      通用文字识别、票据混贴、印章文字识别
      个人证照（身份证、银行卡、社保卡、户口本、护照、驾驶证等）
      行业资质（营业执照、社会团体法人证书等）
      财务票据（增值税发票、火车票、出租车票等）
      金融单据（银行汇票、支票、回单等）

    文件来源二选一：
      file_path: 本地图片绝对路径（如 C:\\Users\\xxx\\image.png）
      file_url:  图片公网下载地址

    Args:
        file_path: 本地图片路径
        file_url: 图片公网下载地址
        ocr_type: 识别类别，默认 GENERAL（通用文字识别）。可用值见 OCR_TYPES 列表。
    """
    cfg = _get_config()
    _check_api_key(cfg["api_key"])

    file_content: bytes
    filename: str
    mime_type: str = "image/png"

    if file_path:
        path = Path(file_path)
        if not path.is_file():
            return {"error": True, "detail": f"文件不存在: {file_path}"}
        file_content = path.read_bytes()
        filename = path.name
        suffix = path.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".bmp": "image/bmp",
            ".tiff": "image/tiff", ".tif": "image/tiff",
            ".webp": "image/webp", ".pdf": "application/pdf",
        }
        mime_type = mime_map.get(suffix, "image/png")
    elif file_url:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            dl_resp = await client.get(file_url)
            if dl_resp.status_code >= 400:
                return {"error": True, "detail": f"下载失败: HTTP {dl_resp.status_code}"}
            file_content = dl_resp.content
            content_type = dl_resp.headers.get("content-type", "")
            if content_type:
                mime_type = content_type.split(";")[0].strip()
            url_path = file_url.split("?")[0]
            filename = url_path.rsplit("/", 1)[-1] or "image.png"
    else:
        return {"error": True, "detail": "请提供 file_path 或 file_url"}

    if ocr_type not in OCR_TYPES:
        return {
            "error": True,
            "detail": f"不支持的 ocr_type: {ocr_type}，可用类型: {OCR_TYPES}",
        }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            cfg["ocr_recognize_url"],
            data={"ocrType": ocr_type},
            files={"file": (filename, file_content, mime_type)},
            headers=_get_form_headers(cfg["api_key"]),
        )
        data = resp.json()

    if resp.status_code >= 400:
        return {"error": True, "status_code": resp.status_code, "detail": data}

    # Simplify result for readability
    extracted = []
    for item in data.get("data", []):
        for result_item in item.get("result", []):
            elements = result_item.get("elements", {})
            stamps = result_item.get("stamps", [])
            entry = {
                "status": result_item.get("status"),
                "filename": result_item.get("originFilename", ""),
                "file_index": result_item.get("fileIndex"),
                "confidence": result_item.get("confidence"),
                "classify_code": result_item.get("classifyCode", ""),
            }
            if elements:
                entry["elements"] = elements
            if stamps:
                entry["stamps"] = stamps
            extracted.append(entry)

    return {
        "success": True,
        "code": data.get("code"),
        "ocr_type": ocr_type,
        "results": extracted,
        "raw": data,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
