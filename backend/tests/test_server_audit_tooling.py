"""Synthetic metadata only. Tests NEVER connect to a server or run real audit commands."""

import importlib.util
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "readonly_server_audit",
    Path(__file__).resolve().parents[2] / "scripts/audit_existing_server.py",
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


@pytest.mark.parametrize(
    "command",
    [
        ["docker", "restart", "existing"],
        [*audit.DOCKER, "stop", "existing"],
        [*audit.DOCKER, "system", "prune"],
        [*audit.DOCKER, "exec", "existing", "cat", "/etc/nginx/nginx.conf"],
        [*audit.DOCKER, "inspect", "existing"],
        [*audit.DOCKER, "compose", "up", "-d"],
        [*audit.DOCKER, "network", "connect", "existing", "new"],
        [*audit.DOCKER, "volume", "rm", "existing"],
        ["nginx", "-s", "reload"],
        ["nginx", "-T"],
        ["nginx", "-t"],
        ["systemctl", "restart", "nginx"],
        ["ufw", "allow", "18443"],
        ["sh", "-c", "anything"],
        [
            "openssl",
            "x509",
            "-in",
            "/etc/ssh/private.key",
            "-noout",
            "-startdate",
            "-enddate",
            "-ext",
            "subjectAltName",
        ],
    ],
)
def test_mutations_unrestricted_inspect_and_private_keys_are_not_allowed(command):
    assert not audit.allowed_command(command)


def test_reader_uses_only_local_docker_socket_and_never_returns_stderr(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=1, stdout="SYNTH-PRIVATE-OUTPUT", stderr="SYNTH-PRIVATE-ERROR"
        )

    monkeypatch.setenv("DOCKER_HOST", "ssh://synthetic-not-the-target")
    monkeypatch.setenv("DOCKER_CONTEXT", "synthetic-remote")
    monkeypatch.setattr(subprocess, "run", fake_run)
    reader = audit.Reader(sudo_readonly=True)
    assert reader.command([*audit.DOCKER, "info", "--format", audit.INFO_FORMAT], True) == (
        False,
        "",
        "",
    )
    command, kwargs = calls[0]
    assert command[:5] == ["sudo", "-n", "--", "docker", "--host=unix:///var/run/docker.sock"]
    assert "DOCKER_HOST" not in kwargs["env"] and "DOCKER_CONTEXT" not in kwargs["env"]
    assert not kwargs.get("shell")
    with pytest.raises(ValueError):
        reader.command([*audit.DOCKER, "system", "prune"])
    assert len(calls) == 1


def test_key_env_and_key_symlink_are_never_read(tmp_path):
    key = tmp_path / "production.key"
    key.write_text("SYNTH-NOT-A-REAL-KEY")
    env = tmp_path / ".env"
    env.write_text("SYNTH-NOT-A-REAL-SECRET")
    link = tmp_path / "site.conf"
    link.symlink_to(key)
    reader = audit.Reader()
    assert reader.config(key) is None
    assert reader.config(env) is None
    assert reader.config(link) is None


def test_ports_include_ipv4_ipv6_udp_and_wildcard():
    result = audit.ports_from_ss(
        "tcp LISTEN 0 128 127.0.0.1:8000 0.0.0.0:*\n"
        "tcp LISTEN 0 128 [::]:443 [::]:*\n"
        "udp UNCONN 0 0 *:8101 *:*\n"
    )
    assert [(row["port"], row["binding"]) for row in result] == [
        (8000, "loopback"),
        (443, "wildcard"),
        (8101, "wildcard"),
    ]


def test_network_supernet_route_and_incomplete_capture_are_not_false_safe():
    assert (
        audit.conflict_result(
            audit.CANDIDATE_NETWORK, [("docker", "network-a", "172.30.0.0/16")], [], True
        )["status"]
        == "FAIL"
    )
    assert (
        audit.conflict_result(
            audit.CANDIDATE_NETWORK, [], [("route", "route-a", "172.16.0.0/12")], True
        )["status"]
        == "FAIL"
    )
    assert (
        audit.conflict_result(
            audit.CANDIDATE_NETWORK,
            [],
            [("route", "default", "0.0.0.0/0"), ("route", "ipv6", "::/0")],
            True,
        )["status"]
        == "PASS"
    )
    assert audit.conflict_result(audit.CANDIDATE_NETWORK, [], [], False)["status"] == "UNVERIFIED"


def test_nginx_metadata_does_not_publish_domains_credentials_uri_or_key_path():
    public, names, certificates, _ = audit.nginx_metadata("""
server_name synthetic-private.example.invalid;
listen 443 ssl;
proxy_pass https://synthetic-user:SYNTH-PASSWORD@127.0.0.1:8101/private-path?token=SYNTH-TOKEN;
ssl_certificate /etc/certificates/public-chain.pem;
ssl_certificate_key /etc/keys/production.key;
proxy_set_header Authorization "Bearer SYNTH-PRIVATE-HEADER";
""")
    text = json.dumps(public)
    for value in (
        "synthetic-private",
        "SYNTH-PASSWORD",
        "private-path",
        "SYNTH-TOKEN",
        "production.key",
        "SYNTH-PRIVATE-HEADER",
    ):
        assert value not in text
    assert names == ["synthetic-private.example.invalid"]
    assert certificates == ["/etc/certificates/public-chain.pem"]
    assert public["proxy_targets"][0]["port"] == 8101
    assert not public["runtime_effective_configuration_verified"]
    assert audit.proxy_summary("http://$dynamic_backend/path")["status"] == "UNVERIFIED"


def test_certificate_dates_sans_and_expiry_are_metadata_only():
    now = datetime(2026, 11, 2, tzinfo=UTC)
    result = audit.certificate_summary(
        "notBefore=Oct  1 00:00:00 2026 GMT\nnotAfter=Dec  1 00:00:00 2026 GMT\n"
        "X509v3 Subject Alternative Name:\n DNS:*.synthetic.example.invalid\n",
        ["mcp.synthetic.example.invalid"],
        now,
    )
    assert result["status"] == "PASS" and result["remaining_days"] == 29
    assert result["matching_domain_aliases"]
    assert "synthetic.example.invalid" not in json.dumps(result)
    assert (
        audit.certificate_summary(
            "notBefore=Oct  1 00:00:00 2025 GMT\nnotAfter=Dec  1 00:00:00 2025 GMT\n", [], now
        )["status"]
        == "FAIL"
    )


class FixtureReader:
    def command(self, argv, privileged=False):
        assert audit.allowed_command(argv)
        args = argv[2:]
        if args[0] == "info":
            value = {"version": "28.0.0", "root": None}
        elif args[0] == "ps":
            return True, "a" * 64 + "\n", ""
        elif args[0] == "inspect":
            value = {
                "id": "a" * 64,
                "name": "SYNTH-PRIVATE-cold-monitor",
                "image": "SYNTH-PRIVATE-image",
                "state": "running",
                "network_mode": "bridge",
                "project": "SYNTH-PRIVATE-project",
                "service": "nginx",
                "ports": {"443/tcp": [{"HostPort": "443", "HostIp": "0.0.0.0"}]},
                "mounts": [{"Type": "volume", "Name": "SYNTH-PRIVATE-data", "RW": True}],
            }
        elif args[:2] == ["network", "ls"]:
            return True, "b" * 64 + "\n", ""
        elif args[:2] == ["network", "inspect"]:
            value = {
                "id": "b" * 64,
                "driver": "bridge",
                "internal": False,
                "ipam": [{"Subnet": "172.30.0.0/16"}],
            }
        elif args[:2] == ["volume", "ls"]:
            return True, "SYNTH-PRIVATE-data\n", ""
        elif args[:2] == ["volume", "inspect"]:
            value = {"name": "SYNTH-PRIVATE-data", "driver": "local"}
        elif args[:2] == ["compose", "version"]:
            return True, "v5.1.3\n", ""
        else:
            raise AssertionError("Unexpected fixture command")
        return True, json.dumps(value), ""


def test_inventory_protects_all_existing_objects_without_raw_names_or_env():
    instance = audit.Audit(FixtureReader())
    public, ports, networks, _, complete = instance.docker_inventory()
    assert complete and public["status"] == "PASS"
    assert "SYNTH-PRIVATE" not in json.dumps(public) + json.dumps(instance.protected)
    assert "cold_monitor" in public["containers"][0]["kind_hints"]
    assert not public["containers"][0]["classification_verified"]
    assert len(instance.protected) >= 4
    assert ports[0]["port"] == 443
    assert (
        audit.conflict_result(audit.CANDIDATE_NETWORK, networks, [], complete)["status"] == "FAIL"
    )
    assert ".Env" not in audit.CONTAINER_FORMAT and ".Cmd" not in audit.CONTAINER_FORMAT
    assert ".Entrypoint" not in audit.CONTAINER_FORMAT and ".Labels}}" not in audit.CONTAINER_FORMAT
