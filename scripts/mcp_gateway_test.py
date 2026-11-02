"""Local-only Docker/HTTPS/PostgreSQL acceptance. Never connects a real tenant or public host."""

import argparse
import asyncio
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import traceback
from pathlib import Path

import httpx2
import jwt
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy/mcp-test/compose.yaml"
DOCKER = ["docker", "--host=unix:///var/run/docker.sock"]
TASK = "FACTORY_OPS_M1_03B_MCP_LIVE_INTEGRATION"
TENANT, AGENT = 7280000000000000031, "agent_synthetic_mcp_gateway"
PLANNED = (
    "isolated_postgresql17_and_migrations",
    "controlled_offline_identity_bootstrap",
    "value_free_jwt_diagnostics",
    "network_and_secret_isolation",
    "public_template_render_only",
    "least_database_privileges",
    "missing_jwt_discovery_refused",
    "invalid_jwt_refused",
    "shared_identity_refused",
    "only_mcp_route_exposed",
    "forwarding_and_origin",
    "untrusted_forwarder_refused",
    "stateless_http_methods",
    "body_and_query_limits",
    "unbound_and_pending_refused",
    "three_roles",
    "cross_factory_and_uuid_refused",
    "grant_revocation_immediate",
    "account_disabled_refused",
    "identity_unbound_refused",
    "audit_failure_closed",
    "database_disconnect_recovery",
    "official_client_tls_and_reconnect",
    "edge_rate_limit",
    "redacted_logs",
    "owned_stack_cleanup",
)


def docker_env():
    env = os.environ.copy()
    for key in (
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_TLS",
        "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH",
    ):
        env.pop(key, None)
    return env


def run(args, *, timeout=120):
    result = subprocess.run(
        args,
        check=False,
        env=docker_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        # Never include child output: Docker/driver failures can contain private configuration.
        raise RuntimeError(
            "A local stack command failed; inspect its private diagnostic file"
        )
    return result.stdout


class Stack:
    def __init__(self, directory):
        self.directory = directory
        self.project = "mcp03b_" + secrets.token_hex(6)
        self.records = [
            {"test": name, "status": "BLOCKED", "evidence": "Not executed yet"}
            for name in PLANNED
        ]
        self.credentials = []
        self.private_log = directory / "commands.log"
        self.env_file = directory / "compose.env"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.origin = f"https://localhost:{self.port}"

    def compose(self, *args, timeout=120, extra_env=None):
        result = subprocess.run(
            [
                *DOCKER,
                "compose",
                "--project-name",
                self.project,
                "--env-file",
                str(self.env_file),
                "--file",
                str(COMPOSE),
                *args,
            ],
            check=False,
            env={**docker_env(), **(extra_env or {})},
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        with self.private_log.open("a") as log:
            log.write(result.stdout + result.stderr)
        self.private_log.chmod(0o600)
        if result.returncode:
            raise RuntimeError(
                "A local compose operation failed; private diagnostics retained"
            )
        return result.stdout

    def prepare(self):
        self.directory.chmod(0o700)
        identities = self.directory / "identities"
        identities.mkdir(mode=0o700)
        for name in (
            "bootstrap_password",
            "runtime_password",
            "operator_password",
            "migrator_password",
            "aily_signing_key",
        ):
            value = secrets.token_urlsafe(48)
            self.credentials.append(value)
            path = self.directory / name
            path.write_text(value)
            # Non-root containers have distinct UIDs. Host confidentiality is enforced by
            # the private 0700 parent; Docker mounts only each service's named readonly files.
            path.chmod(0o444)
        settings = {
            "public_origin": self.origin,
            "tenant_id": str(TENANT),
            "agent_ids": AGENT,
        }
        (self.directory / "identity_settings.json").write_text(json.dumps(settings))
        (self.directory / "identity_settings.json").chmod(0o444)
        (identities / "public-settings.json").write_text(
            json.dumps({"authority": f"localhost:{self.port}"})
        )
        (identities / "public-settings.json").chmod(0o600)
        for index, name in enumerate(
            ("lead", "engineer", "admin", "pending", "unbound")
        ):
            token = self.token(7620000000000000031 + index)
            self.credentials.append(token)
            (identities / (name + ".jwt")).write_text(token)
            (identities / (name + ".jwt")).chmod(0o600)
        run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-keyout",
                str(self.directory / "localhost.key"),
                "-out",
                str(self.directory / "localhost.crt"),
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=DNS:localhost",
            ]
        )
        (self.directory / "localhost.key").chmod(0o444)
        (self.directory / "localhost.crt").chmod(0o444)
        self.env_file.write_text(
            "\n".join(
                [
                    f"MCP_PRIVATE_DIR={self.directory}",
                    f"MCP_HTTPS_PORT={self.port}",
                    f"MCP_PUBLIC_AUTHORITY=localhost:{self.port}",
                    f"MCP_OPERATOR_UID={os.getuid()}",
                    f"MCP_OPERATOR_GID={os.getgid()}",
                    "MCP_BUILD_CA_FILE=/etc/ssl/certs/ca-certificates.crt",
                ]
            )
            + "\n"
        )
        self.env_file.chmod(0o600)

    def token(self, subject=7620000000000000031, **changes):
        return jwt.encode(
            {
                "tenant_id": TENANT,
                "user_id": subject,
                "agent_id": AGENT,
                "exp": int(time.time()) + 3600,
                **changes,
            },
            (self.directory / "aily_signing_key").read_text(),
            algorithm="HS256",
        )

    def check(self, name, evidence):
        row = next(record for record in self.records if record["test"] == name)
        row.update(status="PASS", evidence=evidence)
        print("PASS " + name, flush=True)

    def offline(self, operation, identity="lead", **kwargs):
        arguments = [
            "run",
            "--rm",
            "-T",
            "--no-deps",
            "operator",
            "python",
            "-m",
            "factory_ops.bootstrap_mcp_access",
            operation,
            "--identity-file",
            "/run/identities/" + identity + ".jwt",
            "--reason",
            "SYNTH-APPROVAL-ONLY",
            "--confirm-offline-change",
        ]
        for key, value in kwargs.items():
            if value is True:
                arguments.append("--" + key.replace("_", "-"))
                continue
            for item in value if isinstance(value, list) else [value]:
                arguments += ["--" + key.replace("_", "-"), str(item)]
        output = self.compose(*arguments)
        return json.loads(output.strip())

    def database(self, operation, *args, role="migrate"):
        return json.loads(
            self.compose(
                "run",
                "--rm",
                "-T",
                "--no-deps",
                role,
                "python",
                "/app/mcp-test/database.py",
                operation,
                *args,
            ).strip()
        )

    def setup_accounts(self, factories):
        pending = self.offline("bind")
        lead = self.offline("bootstrap", expected_version=pending["version"])
        people = {"lead": lead}
        for name, role in [
            ("engineer", "engineer"),
            ("admin", "factory_equipment_admin"),
            ("pending", None),
        ]:
            person = self.offline(
                "bind", name, actor_identity_file="/run/identities/lead.jwt"
            )
            if role:
                person = self.offline(
                    "grant",
                    target=person["user_id"],
                    expected_version=person["version"],
                    role=role,
                    factory=[factories["A"]],
                )
            people[name] = person
        return people

    def topology(self):
        services = json.loads(
            self.compose("--profile", "operator", "config", "--format", "json")
        )["services"]
        for name in ("api", "db", "migrate", "read-check", "operator", "probe"):
            assert not services[name].get("ports")
        ports = services["proxy"]["ports"]
        assert len(ports) == 1 and ports[0]["host_ip"] == "127.0.0.1"
        for name in ("api", "proxy"):
            container = self.compose("ps", "-q", name).strip()
            info = json.loads(run([*DOCKER, "inspect", container]))[0]
            assert info["HostConfig"]["ReadonlyRootfs"]
            assert "ALL" in info["HostConfig"]["CapDrop"]
            if name == "api":
                assert not any(info["NetworkSettings"]["Ports"].values())
                assert all(
                    "PASSWORD=" not in field
                    and "JWT_SECRET=" not in field
                    and "DATABASE_URL=" not in field
                    for field in info["Config"]["Env"]
                )
                for network in info["NetworkSettings"]["Networks"]:
                    assert json.loads(run([*DOCKER, "network", "inspect", network]))[0][
                        "Internal"
                    ]
            else:
                assert info["HostConfig"]["PortBindings"] == {
                    "8443/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(self.port)}]
                }
        self.check(
            "network_and_secret_isolation",
            "Only 127.0.0.1 HTTPS published; API/DB private; file secrets",
        )
        rendered = json.loads(
            self.compose(
                "--file",
                str(ROOT / "deploy/mcp-test/compose.public-review.example.yaml"),
                "config",
                "--format",
                "json",
                extra_env={
                    "MCP_APPROVED_PUBLIC_IP": "192.0.2.10",
                    "MCP_PUBLIC_TEST_APPROVAL_REFERENCE": "SYNTH-RENDER-ONLY-NO-DEPLOYMENT",
                },
            )
        )
        assert rendered["services"]["proxy"]["ports"][0]["host_ip"] == "192.0.2.10"
        assert not rendered["services"]["api"].get("ports")
        assert not rendered["services"]["db"].get("ports")
        self.check(
            "public_template_render_only",
            "Config rendered with documentation IP; overlay never started",
        )

    def scan_logs(self):
        logs = self.compose(
            "logs", "--no-color", "--no-log-prefix", "proxy", "api", "db"
        )
        assert all(value not in logs for value in self.credentials)
        assert "SYNTH-URI-SECRET" not in logs
        assert "BEGIN PRIVATE KEY" not in logs
        assert not re.search(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", logs)
        rows = [
            json.loads(line) for line in logs.splitlines() if line.startswith('{"time"')
        ]
        assert rows
        fields = {"time", "request_id", "route", "jwt_present", "status", "seconds"}
        assert all(
            set(row) == fields and isinstance(row["jwt_present"], bool) for row in rows
        )
        assert any(row["status"] == 401 and row["jwt_present"] is False for row in rows)
        assert any(row["jwt_present"] is True for row in rows)
        self.check(
            "redacted_logs",
            "Allowlisted fields and JWT presence boolean only; no credentials/query/body",
        )

    def cleanup(self):
        # Unique owned project only. No external volumes, remote daemon or existing projects.
        assert re.fullmatch(r"mcp03b_[a-f0-9]{12}", self.project)
        self.compose("down", "--volumes", "--remove-orphans", timeout=120)


def tool_error(result):
    assert result["isError"] is True and "structuredContent" not in result
    return json.loads(result["content"][0]["text"])["error"]["code"]


def exercise(stack, data, people):
    context = ssl.create_default_context(cafile=str(stack.directory / "localhost.crt"))
    credentials = {
        name: (stack.directory / "identities" / (name + ".jwt")).read_text()
        for name in people.keys() | {"unbound"}
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }
    with httpx2.Client(
        verify=context, trust_env=False, headers=headers, timeout=20
    ) as http:

        def rpc(method, params=None, identity="lead", **extra_headers):
            time.sleep(
                0.12
            )  # Normal checks stay below the explicitly tested edge rate limit.
            auth = {"x-aily-jwt": credentials[identity]} if identity else {}
            return http.post(
                stack.origin + "/mcp",
                headers={**auth, **extra_headers},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    **({"params": params} if params is not None else {}),
                },
            )

        def call(name, arguments=None, identity="lead"):
            response = rpc(
                "tools/call", {"name": name, "arguments": arguments or {}}, identity
            )
            assert response.status_code == 200
            return response.json()["result"]

        assert rpc("tools/list", identity=None).status_code == 401
        stack.check(
            "missing_jwt_discovery_refused",
            "HTTP401; no anonymous catalogue or shared-token fallback",
        )
        for token in (
            "invalid",
            stack.token(exp=1),
            stack.token(tenant_id=99),
            stack.token(agent_id="wrong_agent"),
            stack.token()[:-8] + "invalid!",
        ):
            assert (
                rpc("tools/list", identity=None, **{"x-aily-jwt": token}).status_code
                == 401
            )
        stack.check(
            "invalid_jwt_refused",
            "Malformed, expired, wrong tenant/agent/signature: HTTP401",
        )
        assert (
            rpc(
                "tools/list",
                identity=None,
                Authorization="Bearer shared",
                **{"x-aily-user": "group_lead"},
            ).status_code
            == 401
        )
        stack.check(
            "shared_identity_refused",
            "Plain identity and shared Bearer do not authenticate",
        )
        for path in (
            "/",
            "/docs",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/access/users",
            "/mcp/",
            "/sse",
        ):
            assert http.get(stack.origin + path).status_code == 404
        stack.check(
            "only_mcp_route_exposed",
            "Docs, API, health, SSE and trailing path all HTTP404",
        )
        assert rpc("tools/list", Host="attacker.invalid").status_code == 421
        assert rpc("tools/list", Origin="https://attacker.invalid").status_code == 403
        assert (
            rpc(
                "tools/list",
                **{"X-Forwarded-Proto": "http", "X-Forwarded-For": "203.0.113.10"},
            ).status_code
            == 200
        )
        stack.check(
            "forwarding_and_origin",
            "Host421/Origin403; forged forwarding overwritten; TLS request works",
        )
        stack.compose("run", "--rm", "-T", "--no-deps", "probe")
        stack.check(
            "untrusted_forwarder_refused",
            "Different internal peer cannot spoof HTTPS scheme: HTTP403",
        )
        for method in ("get", "delete"):
            assert (
                getattr(http, method)(
                    stack.origin + "/mcp", headers={"x-aily-jwt": credentials["lead"]}
                ).status_code
                == 405
            )
        stack.check(
            "stateless_http_methods",
            "Authenticated GET/DELETE405; POST supports Streamable HTTP",
        )
        assert (
            http.post(
                stack.origin + "/mcp",
                content="x" * 16385,
                headers={"x-aily-jwt": credentials["lead"]},
            ).status_code
            == 413
        )
        assert http.get(stack.origin + "/mcp?token=SYNTH-URI-SECRET").status_code == 400
        stack.check(
            "body_and_query_limits",
            "Body >16KiB413; query credentials400; no reflected secrets",
        )
        assert (
            tool_error(call("list_factories", identity="unbound"))
            == "authentication_required"
        )
        assert (
            tool_error(call("list_factories", identity="pending"))
            == "permission_denied"
        )
        stack.check(
            "unbound_and_pending_refused",
            "Business errors; no structuredContent or business data",
        )
        for identity, count in (("lead", 2), ("engineer", 1), ("admin", 1)):
            assert (
                len(
                    call("list_factories", identity=identity)["structuredContent"][
                        "items"
                    ]
                )
                == count
            )
        stack.check(
            "three_roles", "Group2 factories, engineer/admin1; current server grants"
        )
        a, b = data["factories"]["A"], data["factories"]["B"]
        for identity in ("engineer", "admin"):
            assert (
                tool_error(call("search_assets", {"factory_id": b}, identity))
                == "permission_denied"
            )
            assert (
                tool_error(
                    call(
                        "get_asset_detail",
                        {"factory_id": a, "asset_id": data["assets"]["B"]},
                        identity,
                    )
                )
                == "not_found"
            )
        stack.check(
            "cross_factory_and_uuid_refused",
            "Wrong factory permission_denied; foreign asset UUID not_found",
        )
        engineer = people["engineer"]
        engineer = stack.offline(
            "grant",
            target=engineer["user_id"],
            expected_version=engineer["version"],
            role="engineer",
            factory=[a, b],
        )
        assert (
            len(
                call("list_factories", identity="engineer")["structuredContent"][
                    "items"
                ]
            )
            == 2
        )
        engineer = stack.offline(
            "grant",
            target=engineer["user_id"],
            expected_version=engineer["version"],
            role="engineer",
            factory=[a],
        )
        assert (
            tool_error(call("search_assets", {"factory_id": b}, "engineer"))
            == "permission_denied"
        )
        stack.check(
            "grant_revocation_immediate",
            "Same JWT multi-factory grant then revoke; next call denied",
        )
        # Explicit CLI stop-account operation, never an MCP write tool.
        engineer = stack.offline(
            "grant",
            target=engineer["user_id"],
            expected_version=engineer["version"],
            role="pending",
            disable=True,
        )
        assert (
            tool_error(call("list_factories", identity="engineer"))
            == "authentication_required"
        )
        stack.check("account_disabled_refused", "Old JWT cannot query disabled account")
        admin = people["admin"]
        stack.offline(
            "unbind", target=admin["user_id"], expected_version=admin["version"]
        )
        assert (
            tool_error(call("list_factories", identity="admin"))
            == "authentication_required"
        )
        stack.check(
            "identity_unbound_refused", "Same JWT rejected after binding deactivation"
        )
        stack.database("audit-off")
        try:
            assert (
                tool_error(call("search_assets", {"factory_id": a}))
                == "storage_unavailable"
            )
        finally:
            stack.database("audit-on")
        assert (
            call("search_assets", {"factory_id": a})["structuredContent"]["total"] == 1
        )
        stack.check(
            "audit_failure_closed",
            "Revoked INSERT privilege -> no DTO; recovered after controlled restore",
        )
        stack.compose("stop", "db")
        try:
            assert (
                tool_error(call("search_assets", {"factory_id": a}))
                == "storage_unavailable"
            )
        finally:
            stack.compose("up", "-d", "--wait", "db")
        assert (
            call("search_assets", {"factory_id": a})["structuredContent"]["total"] == 1
        )
        stack.check(
            "database_disconnect_recovery",
            "Isolated PostgreSQL stop -> safe error; restart -> fresh successful read",
        )

    async def official_client():
        for _ in range(2):
            async with httpx2.AsyncClient(
                verify=context,
                trust_env=False,
                headers={"x-aily-jwt": credentials["lead"]},
            ) as http:
                transport = streamable_http_client(
                    stack.origin + "/mcp", http_client=http
                )
                async with Client(transport, mode="legacy", cache=None) as client:
                    tools = (await client.list_tools()).tools
                    assert {tool.name for tool in tools} == {
                        "list_factories",
                        "search_assets",
                        "get_asset_detail",
                    }
                    factories = (
                        await client.call_tool("list_factories", {})
                    ).structured_content["items"]
                    factory = next(f for f in factories if f["code"] == "SYNTH-MCP-A")
                    page = await client.call_tool(
                        "search_assets",
                        {"factory_id": factory["id"], "q": "SYNTH-EQ-001"},
                    )
                    asset = page.structured_content["items"][0]
                    detail = await client.call_tool(
                        "get_asset_detail",
                        {"factory_id": factory["id"], "asset_id": asset["id"]},
                    )
                    assert detail.structured_content["name"] == "合成设备 A"
                    assert not {"attachments", "users", "external_identities"} & set(
                        detail.structured_content
                    )
        stack.check(
            "official_client_tls_and_reconnect",
            "Real nginx TLS -> FastAPI -> PostgreSQL; discovery and all3 reads twice",
        )

    asyncio.run(official_client())
    with httpx2.Client(verify=context, trust_env=False, timeout=10) as http:

        async def burst():
            async with httpx2.AsyncClient(
                verify=context, trust_env=False, timeout=10
            ) as client:
                replies = await asyncio.gather(
                    *[
                        client.post(
                            stack.origin + "/mcp",
                            json={
                                "jsonrpc": "2.0",
                                "id": index,
                                "method": "tools/list",
                            },
                        )
                        for index in range(60)
                    ]
                )
            assert any(reply.status_code == 429 for reply in replies)
            assert all(reply.status_code in {401, 429} for reply in replies)
            assert all(
                reply.headers.get("retry-after") == "1"
                for reply in replies
                if reply.status_code == 429
            )

        asyncio.run(burst())
    stack.check(
        "edge_rate_limit",
        "Burst yields429 and Retry-After; missing JWT never yields tool data",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Synthetic-only local HTTPS gateway verification"
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".mcp-gateway-test-results/report.json"),
        help="Sanitized JSON result path",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Create a private local bundle; no services started",
    )
    args = parser.parse_args()
    directory = Path(tempfile.mkdtemp(prefix="factory-ops-mcp03b-")).resolve()
    if directory.is_relative_to(ROOT):
        shutil.rmtree(directory)
        parser.exit(2, "Private runtime directory must be outside the checkout.\n")
    stack = Stack(directory)
    result = {
        "task_id": TASK,
        "checks": stack.records,
        "external": [
            {
                "test": "approved_public_domain_and_deployment",
                "status": "BLOCKED",
                "evidence": "No public deployment authorization/domain/tenant credentials provided",
            },
            {
                "test": "real_aily_discovery_jwt_and_claims",
                "status": "UNVERIFIED",
                "evidence": "Local synthetic JWT validation does not verify actual platform behavior",
            },
            {
                "test": "real_aily_natural_language_and_lifecycle",
                "status": "UNVERIFIED",
                "evidence": "No formal tenant connection or employee/device data used",
            },
        ],
    }
    exit_code = 1
    try:
        run([*DOCKER, "info", "--format", "{{.ServerVersion}}"])
        stack.prepare()
        if args.prepare_only:
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "private_directory": str(directory),
                        "project": stack.project,
                        "origin": stack.origin,
                        "started": False,
                    }
                )
            )
            return 0
        stack.compose("build", "api", timeout=600)
        stack.compose("up", "-d", "--wait", "db", timeout=120)
        stack.database("migrate")
        data = stack.database("seed", "--confirm-synthetic-only")
        stack.check(
            "isolated_postgresql17_and_migrations",
            "Dedicated empty marked DB; current Alembic head; synthetic factories/assets",
        )
        people = stack.setup_accounts(data["factories"])
        stack.check(
            "controlled_offline_identity_bootstrap",
            "Official verifier with synthetic signatures; pending -> first lead -> approved roles",
        )
        diagnostic = json.loads(
            stack.compose(
                "run",
                "--rm",
                "-T",
                "--no-deps",
                "operator",
                "python",
                "/app/mcp-test/inspect_identity.py",
                "/run/identities/lead.jwt",
            )
        )
        assert (
            diagnostic["status"] == "PASS"
            and diagnostic["claim_types"]["user_id"] == "int"
        )
        stack.check(
            "value_free_jwt_diagnostics",
            "Signature/scope verified; only algorithm/types/lifetime output",
        )
        stack.compose("up", "-d", "--wait", "api", "proxy", timeout=180)
        stack.topology()
        stack.database("privileges", role="read-check")
        stack.check(
            "least_database_privileges",
            "12 forbidden DDL/DML/session/audit/escalation operations denied by PostgreSQL",
        )
        exercise(stack, data, people)
        stack.scan_logs()
        exit_code = 0
    except Exception:  # noqa: BLE001 -- CLI boundary must never print raw credentials/errors.
        detail = traceback.format_exc()
        try:
            stack.compose(
                "logs",
                "--no-color",
                "--no-log-prefix",
                "proxy",
                "api",
                "db",
                timeout=10,
            )
        except (RuntimeError, OSError, subprocess.SubprocessError):
            pass
        for value in stack.credentials:
            detail = detail.replace(value, "[REDACTED]")
        with stack.private_log.open("a") as log:
            log.write(detail)
        stack.private_log.chmod(0o600)
        stack.records.append(
            {
                "test": "local_stack_acceptance",
                "status": "FAIL",
                "evidence": "A check failed; private diagnostics are not uploaded",
            }
        )
        print(
            "FAIL local_stack_acceptance; private diagnostics: "
            + str(stack.private_log)
        )
    finally:
        if not args.prepare_only:
            try:
                stack.cleanup()
                stack.check(
                    "owned_stack_cleanup", "Owned containers/networks/volume removed"
                )
            except (RuntimeError, OSError, subprocess.SubprocessError):
                exit_code = 1
                stack.records.append(
                    {
                        "test": "owned_stack_cleanup",
                        "status": "FAIL",
                        "evidence": "Manual cleanup of unique local project required",
                    }
                )
            if exit_code == 0:
                shutil.rmtree(directory)
            # On failure retain only private diagnostics; still destroy credentials and TLS keys.
            else:
                for path in directory.rglob("*"):
                    if path.is_file() and path.name != "commands.log":
                        path.unlink()
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
