"""Public build failure diagnostics must not expose credentials or opaque tokens."""

import importlib.util
import secrets
from pathlib import Path

import jwt


def test_build_diagnostic_redacts_secret_tokens_urls_and_private_paths():
    script = Path(__file__).resolve().parents[2] / "scripts/mcp_gateway_test.py"
    spec = importlib.util.spec_from_file_location("mcp_gateway_tooling", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    key, opaque = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    token = jwt.encode({"user_id": 1, "exp": 9999999999}, key, algorithm="HS256")
    source = (
        f"{key} {opaque} {token} /private/synthetic/compose.env "
        "https://synthetic-user:synthetic-pass@example.invalid/path?token=secret "
        "ERROR: buildx prerequisite missing"
    )
    result = module.safe_build_error(source, [key], Path("/private/synthetic"))
    for value in [key, opaque, token, "/private/synthetic", "synthetic-pass", "token=secret"]:
        assert value not in result
    assert "ERROR: buildx prerequisite missing" in result
    assert len(result) <= 1800
