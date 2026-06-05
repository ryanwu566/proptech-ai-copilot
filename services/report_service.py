"""HTML report generation for TaxOracle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.schemas import TaxCase


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "reports" / "templates"


def generate_tax_html_report(case: TaxCase, result: dict[str, Any]) -> str:
    """Render a downloadable UTF-8 TaxOracle HTML report."""

    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = environment.get_template("tax_report.html")
    return template.render(case=case, result=result)
