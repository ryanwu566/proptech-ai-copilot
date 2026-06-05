"""Optional LLM explanation service with an offline fallback."""

from __future__ import annotations

import os
from typing import Any


def build_ai_report_prompt(result: dict[str, Any]) -> str:
    """Build a constrained prompt for an optional future OpenAI integration."""

    return (
        "請只根據以下 structured result 改寫中文說明。不可修改資格、分數或新增法規結論：\n"
        f"{result}"
    )


def generate_ai_explanation(result: dict[str, Any]) -> dict[str, str]:
    """Return a stable Chinese fallback explanation.

    OPENAI_API_KEY is intentionally optional in this MVP. A later integration
    may use build_ai_report_prompt while preserving the deterministic result.
    """

    status_map = {
        "eligible": "目前初步規則檢核皆通過，可進一步整理申報文件。",
        "manual_review": "目前有條件需要補件或人工複核，建議先完成文件確認。",
        "not_eligible": "目前存在未通過的必要條件，建議交由專業人士確認替代方案。",
    }
    source = "模板 fallback" if not os.getenv("OPENAI_API_KEY") else "模板模式（尚未啟用外部 API）"
    return {
        "headline": status_map[result["eligibility_status"]],
        "customer_script": "房仲可先向客戶說明這是初步風險盤點，再依補件清單準備資料。",
        "source": source,
    }

