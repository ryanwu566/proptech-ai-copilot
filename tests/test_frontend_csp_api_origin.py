from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEXT_CONFIG = ROOT / "frontend_next/next.config.mjs"


def _content_security_policy(api_base_url: str | None) -> str:
    script = """
      import { pathToFileURL } from "node:url";
      const configPath = process.argv[1];
      const mod = await import(pathToFileURL(configPath).href);
      const entries = await mod.default.headers();
      const headers = entries[0].headers;
      const csp = headers.find((header) => header.key === "Content-Security-Policy");
      if (!csp) {
        throw new Error("missing Content-Security-Policy");
      }
      process.stdout.write(csp.value);
    """
    env = os.environ.copy()
    if api_base_url is None:
        env.pop("NEXT_PUBLIC_API_BASE_URL", None)
    else:
        env["NEXT_PUBLIC_API_BASE_URL"] = api_base_url

    result = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(NEXT_CONFIG)],
        check=True,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _directives(csp: str) -> dict[str, str]:
    pairs = {}
    for directive in csp.split(";"):
        directive = directive.strip()
        if not directive:
            continue
        name, _, value = directive.partition(" ")
        pairs[name] = value
    return pairs


def test_csp_connect_src_allows_configured_production_api_origin() -> None:
    csp = _content_security_policy("https://proptech-ai-copilot-api.onrender.com")
    directives = _directives(csp)

    assert directives["connect-src"] == "'self' https://proptech-ai-copilot-api.onrender.com"
    connect_tokens = directives["connect-src"].split()
    assert "https:" not in connect_tokens
    assert "*.onrender.com" not in connect_tokens


def test_csp_connect_src_strips_api_url_path_to_origin() -> None:
    csp = _content_security_policy("https://proptech-ai-copilot-api.onrender.com/market-insights/query?x=1")
    directives = _directives(csp)

    assert directives["connect-src"] == "'self' https://proptech-ai-copilot-api.onrender.com"
    assert "/market-insights" not in directives["connect-src"]


def test_csp_connect_src_keeps_e2e_origin() -> None:
    csp = _content_security_policy("http://e2e.test")
    assert _directives(csp)["connect-src"] == "'self' http://e2e.test"


def test_csp_connect_src_rejects_invalid_or_insecure_api_url() -> None:
    assert _directives(_content_security_policy("not a url"))["connect-src"] == "'self'"
    assert _directives(_content_security_policy("http://api.example.invalid"))["connect-src"] == "'self'"
    assert _directives(_content_security_policy(None))["connect-src"] == "'self'"


def test_csp_preserves_existing_security_directives() -> None:
    directives = _directives(_content_security_policy("https://proptech-ai-copilot-api.onrender.com"))

    assert directives["default-src"] == "'self'"
    assert directives["script-src"] == "'self' 'unsafe-inline'"
    assert directives["style-src"] == "'self' 'unsafe-inline'"
    assert directives["img-src"] == "'self' data: blob: https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com https://server.arcgisonline.com"
    assert directives["object-src"] == "'none'"
    assert directives["base-uri"] == "'self'"
    assert directives["frame-ancestors"] == "'none'"
    assert directives["form-action"] == "'self'"
