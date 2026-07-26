import json
import subprocess
import sys

from scripts.import_plvr_to_postgres import classify_import_readiness, main


def report(**overrides):
    value = {"read_rows": 100, "accepted_rows": 90, "excluded_rows": 10, "skipped_duplicate_rows": 2, "source_periods": ["2026-01", "2026-02"], "cities": ["虛構市"], "city_scope": ["虛構市"], "is_dry_run": True, "status": "dry_run"}
    value.update(overrides)
    return value


def test_import_readiness_pass_warning_and_blocked() -> None:
    assert classify_import_readiness(report())["quality_status"] == "pass"
    assert "high_exclusion_ratio" in classify_import_readiness(report(excluded_rows=30))["quality_reason_codes"]
    assert classify_import_readiness(report(accepted_rows=0))["quality_status"] == "blocked"
    assert classify_import_readiness(report(source_periods=[]))["quality_status"] == "blocked"


def test_zero_rows_have_null_ratios() -> None:
    result = classify_import_readiness(report(read_rows=0, accepted_rows=0, excluded_rows=0, skipped_duplicate_rows=0, source_periods=[]))
    assert result["accepted_ratio"] is None
    assert result["exclusion_ratio"] is None
    assert result["duplicate_ratio"] is None


def test_report_output_is_safe_and_atomic(tmp_path, capsys) -> None:
    source = tmp_path / "a_lvr_land_a.csv"
    source.write_text("鄉鎮市區,交易標的,土地位置建物門牌,交易年月日,建物移轉總面積平方公尺,總價元\n大安區,房地(土地+建物),虛構路1號,1150101,30,3000000\n", encoding="utf-8-sig")
    output = tmp_path / "nested" / "report.json"
    assert main(["--input", str(source), "--city", "虛構市", "--dry-run", "--report-output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["report_schema_version"] == "plvr-import-readiness-v1"
    assert "虛構路" not in output.read_text(encoding="utf-8")
    assert "database" not in output.read_text(encoding="utf-8").lower()
    assert "PLVR 匯入未完成" not in capsys.readouterr().out


def test_quality_gate_blocked_exit_and_audit_cli(tmp_path) -> None:
    source = tmp_path / "a_lvr_land_a.csv"
    source.write_text("鄉鎮市區,交易標的,土地位置建物門牌,交易年月日,建物移轉總面積平方公尺,總價元\n,,,,,\n", encoding="utf-8-sig")
    output = tmp_path / "report.json"
    assert main(["--input", str(source), "--city", "虛構市", "--dry-run", "--report-output", str(output), "--quality-gate"]) == 2
    result = subprocess.run([sys.executable, "scripts/audit_plvr_import_report.py", "--input", str(output)], text=True, capture_output=True, check=False)
    assert result.returncode == 2
    assert "PLVR_IMPORT_REPORT=blocked" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr
