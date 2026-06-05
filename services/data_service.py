"""Friendly mock data loading helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


class MockDataError(RuntimeError):
    """Raised when a bundled CSV cannot be loaded for the demo."""


def load_mock_csv(name: str) -> pd.DataFrame:
    """Load a bundled mock CSV and provide a user-friendly error."""

    path = DATA_DIR / name
    if not path.exists():
        raise MockDataError(f"找不到展示資料：{name}。請確認 data 資料夾內容完整。")
    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise MockDataError(f"無法讀取展示資料：{name}。請檢查 CSV 格式。") from exc
