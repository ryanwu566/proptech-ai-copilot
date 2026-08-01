from __future__ import annotations

from scripts.production_ops_gate import evaluate


def test_production_operations_gate_passes_without_external_services() -> None:
    result = evaluate()
    assert result["status"] == "pass"
    assert result["missing"] == []
