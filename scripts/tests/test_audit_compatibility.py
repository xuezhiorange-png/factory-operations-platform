"""Run unchanged on real Python 3.10/3.11/3.12; no host inventory or server access."""

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "audit_existing_server.py"
SPEC = importlib.util.spec_from_file_location("audit_compatibility", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_default_certificate_clock_is_timezone_aware():
    result = audit.certificate_summary(
        "notBefore=Jan  1 00:00:00 2000 GMT\nnotAfter=Jan  1 00:00:00 2999 GMT\n",
        [],
    )
    assert result["status"] == "PASS"
    assert datetime.fromisoformat(result["not_after_utc"]).utcoffset() == timedelta(0)


def test_synthetic_collection_serializes_utc_and_preserves_blocked_state(monkeypatch):
    class OfflineReader:
        def command(self, argv, privileged=False):
            assert audit.allowed_command(argv)
            return False, "", ""

        def config(self, path):
            raise AssertionError("Synthetic collection must not read host configuration")

    def deny_subprocess(*args, **kwargs):
        raise AssertionError("Synthetic collection must not execute host commands")

    def synthetic_text(path, *args, **kwargs):
        assert str(path) == "/proc/meminfo"
        return "MemTotal: 2048 kB\nMemAvailable: 1024 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n"

    monkeypatch.setattr(subprocess, "run", deny_subprocess)
    monkeypatch.setattr(Path, "read_text", synthetic_text)
    monkeypatch.setattr(Path, "is_file", lambda path: False)
    monkeypatch.setattr(Path, "is_dir", lambda path: False)
    monkeypatch.setattr(audit.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        audit.shutil, "disk_usage", lambda path: SimpleNamespace(total=4096, free=2048)
    )
    monkeypatch.setattr(audit.os, "cpu_count", lambda: 2)
    monkeypatch.setattr(audit.os, "getloadavg", lambda: (0.0, 0.0, 0.0))

    report = json.loads(json.dumps(audit.Audit(OfflineReader()).collect()))
    timestamp = datetime.fromisoformat(report["collected_at_utc"])
    assert timestamp.tzinfo == timezone.utc
    assert report["ready_for_deployment"] == "NO"
    assert report["docker"]["status"] == "BLOCKED"
    assert report["network_conflicts"]["status"] == "UNVERIFIED"
    assert all(row["status"] == "UNVERIFIED" for row in report["port_checks"])


@pytest.mark.parametrize("arguments,exit_code", [(["--help"], 0), ([], 2)])
def test_real_interpreter_accepts_stdin_and_never_collects_without_opt_in(
    arguments, exit_code, tmp_path
):
    result = subprocess.run(
        [sys.executable, "-B", "-", *arguments],
        input=SCRIPT.read_text(encoding="utf-8"),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
        cwd=tmp_path,
    )
    assert result.returncode == exit_code
    assert "--collect" in result.stdout + result.stderr
    assert '"collected_at_utc"' not in result.stdout
    assert list(tmp_path.iterdir()) == []
