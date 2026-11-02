"""Execute the copied Mac command with synthetic curl/SSH only; no network access."""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "payload,ssh_exit,save_report",
    [
        ('{"mode":"READ_ONLY","ready_for_deployment":"NO"}\n', 0, True),
        ('{"status":"BLOCKED","ready_for_deployment":"NO"}\n', 1, True),
        ("synthetic transport failure\n", 255, False),
    ],
)
def test_mac_command_uses_stdin_strict_identity_and_validates_before_saving(
    payload, ssh_exit, save_report, tmp_path
):
    runbook = (ROOT / "docs/operations/EXISTING_SERVER_READONLY_AUDIT.md").read_text()
    command = re.search(
        r"<!-- mac-audit-command:start -->\s*```bash\n(.*?)\n```", runbook, re.DOTALL
    ).group(1)
    syntax = subprocess.run(
        ["bash", "-n"], input=command, text=True, capture_output=True, check=False
    )
    assert syntax.returncode == 0

    # Substitute the user's two placeholders and the Mac output path with local fixtures.
    key = tmp_path / "synthetic test key"
    key.write_text("SYNTHETIC-NOT-A-PRIVATE-KEY")
    output = tmp_path / "factory-ops-server-audit.json"
    previous = '{"previous":"synthetic-report"}\n'
    output.write_text(previous)
    command = command.replace(
        "AUDIT_SSH_USER='替换为已有授权SSH用户名'", "AUDIT_SSH_USER='synthetic-auditor'"
    ).replace(
        'AUTHORIZED_SSH_KEY="$HOME/.ssh/替换为已有授权私钥文件名"',
        "AUTHORIZED_SSH_KEY=" + shlex.quote(str(key)),
    ).replace(
        'AUDIT_OUTPUT="$HOME/factory-ops-server-audit.json"',
        "AUDIT_OUTPUT=" + shlex.quote(str(output)),
    )
    driver = tmp_path / "synthetic_transport.py"
    driver.write_text(
        "import json, os, sys\nfrom pathlib import Path\n"
        "tool, args = sys.argv[1], sys.argv[2:]\n"
        "record = {'arguments': args}\n"
        "if tool == 'curl':\n"
        "    Path(args[args.index('--output') + 1]).write_bytes(\n"
        "        Path(os.environ['AUDIT_TEST_SOURCE']).read_bytes())\n"
        "else:\n"
        "    record['stdin'] = sys.stdin.read()\n"
        "    sys.stdout.write(os.environ['AUDIT_TEST_REPORT'])\n"
        "Path(os.environ['AUDIT_TEST_CAPTURE'], tool + '.json').write_text(json.dumps(record))\n"
        "sys.exit(int(os.environ['AUDIT_TEST_SSH_EXIT']) if tool == 'ssh' else 0)\n"
    )
    binaries = tmp_path / "synthetic-bin"
    binaries.mkdir()
    for tool in ("curl", "ssh"):
        executable = binaries / tool
        executable.write_text(
            '#!/bin/sh\nexec "$AUDIT_TEST_PYTHON" "$AUDIT_TEST_DRIVER" ' + tool + ' "$@"\n'
        )
        executable.chmod(0o700)
    python = binaries / "python3"
    python.write_text('#!/bin/sh\nexec "$AUDIT_TEST_PYTHON" "$@"\n')
    python.chmod(0o700)
    environment = os.environ.copy()
    environment.update(
        PATH=str(binaries) + os.pathsep + environment["PATH"],
        TMPDIR=str(tmp_path),
        AUDIT_TEST_PYTHON=sys.executable,
        AUDIT_TEST_DRIVER=str(driver),
        AUDIT_TEST_SOURCE=str(ROOT / "scripts/audit_existing_server.py"),
        AUDIT_TEST_CAPTURE=str(tmp_path),
        AUDIT_TEST_REPORT=payload,
        AUDIT_TEST_SSH_EXIT=str(ssh_exit),
    )
    result = subprocess.run(
        ["bash", "-c", command], env=environment, cwd=tmp_path,
        text=True, capture_output=True, timeout=10, check=False,
    )
    capture = json.loads((tmp_path / "ssh.json").read_text())
    arguments = capture["arguments"]
    for option in (
        "BatchMode=yes", "StrictHostKeyChecking=yes", "UpdateHostKeys=no",
        "ConnectTimeout=8", "ConnectionAttempts=1", "IdentitiesOnly=yes",
    ):
        assert option in arguments
    assert "-T" in arguments
    assert arguments[arguments.index("-i") + 1] == str(key)
    assert arguments[-2] == "synthetic-auditor@156.238.241.139"
    assert arguments[-1] == "PYTHONDONTWRITEBYTECODE=1 python3 -B - --collect"
    assert capture["stdin"] == (ROOT / "scripts/audit_existing_server.py").read_text()
    download = json.loads((tmp_path / "curl.json").read_text())["arguments"]
    assert download[download.index("--proto") + 1] == "=https"
    assert download[download.index("--proto-redir") + 1] == "=https"
    assert not {"--insecure", "-k"}.intersection(download)
    if save_report:
        assert result.returncode == ssh_exit
        assert json.loads(output.read_text())["ready_for_deployment"] == "NO"
    else:
        assert result.returncode != 0
        assert output.read_text() == previous
