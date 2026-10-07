"""Exercise the canonical E9 model instead of retired UI source assertions."""
import json
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def probe_models() -> dict:
    script = """
      import {e9Case} from './frontend_next/lib/workspace/e9-test-fixtures.ts';
      import {adaptSavedCaseToWorkspace} from './frontend_next/lib/workspace/legacy-case-adapter.ts';
      import {projectCaseEvidence} from './frontend_next/lib/workspace/case-evidence.ts';
      import {buildComparisonModel,buildReportModel,compareHref} from './frontend_next/lib/workspace/compare-report-model.ts';
      const cases=['case-a','case-b','case-c','case-d','case-e'].map(id=>projectCaseEvidence(adaptSavedCaseToWorkspace(e9Case(id))));
      const two=buildComparisonModel(cases,['case-b','case-a']);
      const four=buildComparisonModel(cases,['case-d','case-a','case-c','case-b']);
      const report=buildReportModel(cases[0],'2026-10-07T04:00:00Z');
      console.log(JSON.stringify({two,four,
        five:buildComparisonModel(cases,cases.map(c=>c.caseId)).status,
        duplicate:buildComparisonModel(cases,['case-a','case-a']).status,
        missing:buildComparisonModel(cases,['case-a','missing']).status,
        one:buildComparisonModel(cases,['case-a']).status,
        href:compareHref(['case-b','case-a']), report}));
    """
    return json.loads(subprocess.check_output(
        ["node", "--disable-warning=MODULE_TYPELESS_PACKAGE_JSON", "--input-type=module", "-e", script],
        cwd=ROOT, text=True, encoding="utf-8",
    ))
