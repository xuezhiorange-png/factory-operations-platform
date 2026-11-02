"""Read-only Linux inventory. Standard library only; JSON output contains metadata aliases.

Run on the intended server via existing trusted SSH or its console. No file writes, docker
exec, config validation/reload, database connections, firewall commands or credential reads.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

PORTS = (22, 80, 443, 3001, 8000, 8101, 18443)
CANDIDATE_NETWORK = "172.30.83.0/28"
DOCKER = ("docker", "--host=unix:///var/run/docker.sock")
LIMIT = 256
CONTAINER_FORMAT = (
    '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Config.Image}},'
    '"state":{{json .State.Status}},"network_mode":{{json .HostConfig.NetworkMode}},'
    '"ports":{{json .NetworkSettings.Ports}},"mounts":{{json .Mounts}},'
    '"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
    '"service":{{json (index .Config.Labels "com.docker.compose.service")}}}'
)
NETWORK_FORMAT = '{"id":{{json .Id}},"driver":{{json .Driver}},"internal":{{json .Internal}},"ipam":{{json .IPAM.Config}}}'
VOLUME_FORMAT = '{"name":{{json .Name}},"driver":{{json .Driver}}}'
INFO_FORMAT = '{"version":{{json .ServerVersion}},"cpus":{{json .NCPU}},"memory":{{json .MemTotal}},"root":{{json .DockerRootDir}}}'
SENSITIVE_PATH = re.compile(
    r"(?:^|[/_.-])(secrets?|passwords?|passwd|tokens?|private|id_rsa|id_ed25519|authorized_keys|known_hosts|credentials|ssh)(?:$|[/_.-])",
    re.IGNORECASE,
)


def alias(kind, value):
    if kind in {"container", "network"} and re.fullmatch(
        r"[a-f0-9]{12,64}", str(value)
    ):
        return kind + "-" + str(value)[:12]
    return kind + "-" + hashlib.sha256(str(value).encode()).hexdigest()[:12]


def family(value):
    text = str(value).lower()
    for kind, pattern in (
        ("cold_monitor", r"cold.*monitor|cold.*watch|refrig.*monitor|冷库.*监控"),
        ("cold_planning", r"cold.*plan|cold.*layout|冷库.*规划"),
        ("nginx", r"nginx"),
        ("postgresql", r"postgres|pgsql"),
        ("mysql", r"mysql|mariadb"),
        ("redis", r"redis"),
        ("ssh", r"sshd?|openssh"),
        ("docker", r"docker|containerd"),
    ):
        if re.search(pattern, text):
            return kind
    return "unclassified"


def binding(value):
    if value in {"*", ""}:
        return "wildcard"
    try:
        addr = ipaddress.ip_address(value.strip("[]"))
        return (
            "loopback"
            if addr.is_loopback
            else "wildcard"
            if addr.is_unspecified
            else "specific_address"
        )
    except ValueError:
        return "unknown"


def allowed_command(argv):
    """Defense against accidental expansion into service control or unrestricted inspection."""
    if tuple(argv[:2]) == DOCKER:
        args = argv[2:]
        if args in (
            ["ps", "-aq", "--no-trunc"],
            ["network", "ls", "-q"],
            ["volume", "ls", "-q"],
            ["compose", "version", "--short"],
        ):
            return True
        if args == ["info", "--format", INFO_FORMAT]:
            return True
        if len(args) == 4 and args[:3] == ["inspect", "--format", CONTAINER_FORMAT]:
            return bool(re.fullmatch(r"[a-f0-9]{12,64}", args[3]))
        if len(args) == 5 and args[:4] == [
            "network",
            "inspect",
            "--format",
            NETWORK_FORMAT,
        ]:
            return bool(re.fullmatch(r"[a-f0-9]{12,64}", args[4]))
        if len(args) == 5 and args[:4] == [
            "volume",
            "inspect",
            "--format",
            VOLUME_FORMAT,
        ]:
            return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", args[4]))
        return False
    if argv in (
        ["ss", "-H", "-lntu"],
        ["ip", "-j", "route", "show", "table", "all"],
        [
            "systemctl",
            "list-units",
            "--type=service",
            "--state=running",
            "--no-legend",
            "--no-pager",
            "--plain",
        ],
    ):
        return True
    if len(argv) == 2 and Path(argv[0]).name == "nginx" and argv[1] == "-v":
        return True
    return bool(
        len(argv) == 9
        and argv[:3] == ["openssl", "x509", "-in"]
        and argv[4:] == ["-noout", "-startdate", "-enddate", "-ext", "subjectAltName"]
        and argv[3].startswith("/")
        and not SENSITIVE_PATH.search(str(Path(argv[3]).resolve()))
        and Path(argv[3]).resolve().suffix.lower() != ".key"
    )


class Reader:
    def __init__(self, sudo_readonly=False):
        self.sudo_readonly = sudo_readonly

    def command(self, argv, privileged=False):
        if not allowed_command(argv):
            raise ValueError("Command outside the read-only allowlist")
        env = os.environ.copy()
        for key in (
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_TLS",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
        ):
            env.pop(key, None)
        env.update(LC_ALL="C", PYTHONDONTWRITEBYTECODE="1")
        command = (
            ["sudo", "-n", "--"] if privileged and self.sudo_readonly else []
        ) + argv
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=env,
            )
            # Never expose stderr, arguments, environment or raw inspect/config output.
            return (
                (True, result.stdout[:1048576], result.stderr[:4096])
                if result.returncode == 0
                else (False, "", "")
            )
        except (OSError, subprocess.TimeoutExpired):
            return False, "", ""

    def config(self, path):
        """Read configuration only, never key/env/password files or arbitrary paths."""
        path = Path(path)
        try:
            if (
                SENSITIVE_PATH.search(str(path.resolve()))
                or path.resolve().name == ".env"
                or path.resolve().name.startswith(".env.")
                or path.resolve().suffix.lower() in {".key", ".pem", ".env"}
                or path.suffix.lower() in {".key", ".pem", ".env"}
                or not path.is_file()
                or path.stat().st_size > 1048576
            ):
                return None
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None


def ports_from_ss(text):
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0] not in {"tcp", "udp"}:
            continue
        endpoint = fields[4]
        address, separator, port = endpoint.rpartition(":")
        if separator and port.isdigit():
            rows.append(
                {"protocol": fields[0], "port": int(port), "binding": binding(address)}
            )
    return rows


def conflict_result(candidate, networks, routes, complete=True):
    wanted = ipaddress.ip_network(candidate)
    overlaps = []
    for source, reference, cidr in [*networks, *routes]:
        try:
            existing = ipaddress.ip_network(cidr, strict=False)
            if (
                existing.prefixlen
                and existing.version == wanted.version
                and wanted.overlaps(existing)
            ):
                overlaps.append(
                    {
                        "source": source,
                        "reference": reference,
                        "prefix_length": existing.prefixlen,
                    }
                )
        except ValueError:
            continue
    return {
        "candidate": candidate,
        "status": "FAIL" if overlaps else "PASS" if complete else "UNVERIFIED",
        "conflicts": overlaps,
        "scope": "Docker IPAM plus non-default host routes; snapshot only",
    }


def proxy_summary(value):
    """Do not return URI paths, credentials, query strings, hostnames or upstream names."""
    try:
        target = urlsplit(value.strip("\"'"))
        if (
            target.scheme not in {"http", "https"}
            or not target.hostname
            or "$" in value
        ):
            return {"kind": "dynamic_or_unresolved", "status": "UNVERIFIED"}
        host = target.hostname
        kind = (
            "loopback"
            if host in {"localhost", "127.0.0.1", "::1"}
            else "non_loopback_or_upstream_group"
        )
        return {
            "scheme": target.scheme,
            "target": alias("upstream", host),
            "kind": kind,
            "port": target.port
            or (
                (443 if target.scheme == "https" else 80)
                if kind == "loopback"
                else None
            ),
            "upstream_resolution_verified": False,
        }
    except ValueError:
        return {"kind": "dynamic_or_unresolved", "status": "UNVERIFIED"}


def nginx_metadata(text):
    domains, certificates, proxies, listeners, includes = [], [], [], [], []
    # Deliberately static and conservative: not an effective-config or running-config claim.
    for match in re.finditer(
        r"(?m)^\s*(server_name|ssl_certificate|proxy_pass|listen|include)\s+([^;{}]*);",
        text,
    ):
        directive, value = match.groups()
        if directive == "server_name":
            domains.extend(
                name for name in value.split() if name != "_" and "$" not in name
            )
        elif directive == "ssl_certificate":
            certificates.append(value.strip().strip("\"'"))
        elif directive == "proxy_pass":
            proxies.append(proxy_summary(value))
        elif directive == "listen":
            endpoint = value.split()[0]
            port = endpoint.rsplit(":", 1)[-1]
            if port.isdigit():
                listeners.append(int(port))
        else:
            includes.append(value.strip().strip("\"'"))
    public = {
        "domains": sorted({alias("domain", name.lower()) for name in domains}),
        "listen_ports": sorted(set(listeners)),
        "proxy_targets": proxies,
        "include_directives": len(includes),
        "static_scan_only": True,
        "runtime_effective_configuration_verified": False,
    }
    return public, domains, certificates, includes


def certificate_summary(output, domains, now=None):
    now = now or datetime.now(timezone.utc)
    dates = {}
    for field in ("notBefore", "notAfter"):
        match = re.search(field + r"=(.+)", output)
        if match:
            try:
                dates[field] = datetime.strptime(
                    match[1].strip(), "%b %d %H:%M:%S %Y %Z"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
    sans = re.findall(r"DNS:([^,\s]+)", output)
    matches = []
    for domain in domains:
        if any(
            domain.lower() == san.lower()
            or san.startswith("*.")
            and domain.lower().endswith(san[1:].lower())
            and domain.count(".") == san.count(".")
            for san in sans
        ):
            matches.append(alias("domain", domain.lower()))
    valid = bool(
        dates.get("notBefore")
        and dates.get("notAfter")
        and dates["notBefore"] <= now < dates["notAfter"]
    )
    return {
        "status": "PASS" if valid else "FAIL" if len(dates) == 2 else "UNVERIFIED",
        "not_after_utc": dates["notAfter"].isoformat() if "notAfter" in dates else None,
        "remaining_days": (dates["notAfter"] - now).days
        if "notAfter" in dates
        else None,
        "dns_san_count": len(sans),
        "matching_domain_aliases": sorted(set(matches)),
        "scope": "Local public certificate dates/SAN only; public TLS chain/served cert unverified",
    }


class Audit:
    def __init__(self, reader):
        self.reader = reader
        self.protected = []

    def json_command(self, args, privileged=True):
        ok, stdout, _ = self.reader.command(list(args), privileged)
        if not ok:
            return None
        try:
            return json.loads(stdout)
        except (ValueError, TypeError):
            return None

    def docker_inventory(self):
        info = self.json_command([*DOCKER, "info", "--format", INFO_FORMAT])
        ok, ids, _ = self.reader.command([*DOCKER, "ps", "-aq", "--no-trunc"], True)
        containers, sockets, config_roots = [], [], []
        complete = bool(ok and info)
        identifiers = ids.splitlines()
        if len(identifiers) > LIMIT:
            complete = False
        for container_id in identifiers[:LIMIT]:
            raw = self.json_command(
                [*DOCKER, "inspect", "--format", CONTAINER_FORMAT, container_id]
            )
            if not raw:
                complete = False
                continue
            reference = alias("container", raw["id"])
            hints = sorted(
                {
                    family(raw.get(key, ""))
                    for key in ("name", "image", "project", "service")
                }
                - {"unclassified"}
            )
            published = []
            for target, bindings in (raw.get("ports") or {}).items():
                for entry in bindings or []:
                    port = str(entry.get("HostPort", ""))
                    if port.isdigit():
                        row = {
                            "protocol": target.split("/")[-1],
                            "port": int(port),
                            "binding": binding(entry.get("HostIp", "")),
                            "container": reference,
                            "container_port": int(target.split("/")[0])
                            if target.split("/")[0].isdigit()
                            else None,
                        }
                        published.append(row)
                        sockets.append(row)
            mounts = []
            for mount in raw.get("mounts") or []:
                ref = alias(
                    "volume" if mount["Type"] == "volume" else "bind",
                    mount.get("Name") or mount.get("Source"),
                )
                mounts.append(
                    {
                        "reference": ref,
                        "type": mount["Type"],
                        "writable": mount.get("RW"),
                    }
                )
                self.protected.append(
                    {
                        "resource": ref,
                        "reason": "Existing mount; never attach, overwrite or delete",
                    }
                )
                destination = mount.get("Destination", "")
                if (
                    "nginx" in hints
                    and destination.startswith("/etc/nginx")
                    and mount["Type"] == "bind"
                ):
                    config_roots.append(mount.get("Source", ""))
            containers.append(
                {
                    "reference": reference,
                    "kind_hints": hints or ["unclassified"],
                    "classification_verified": False,
                    "state": raw.get("state"),
                    "host_network": raw.get("network_mode") == "host",
                    "ports": published,
                    "mounts": mounts,
                }
            )
            self.protected.append(
                {
                    "resource": reference,
                    "reason": "Existing service, including cold monitor/planning candidates; no stop/restart/exec",
                }
            )
        ok_net, network_ids, _ = self.reader.command(
            [*DOCKER, "network", "ls", "-q"], True
        )
        networks, ranges = [], []
        for identifier in network_ids.splitlines()[:LIMIT]:
            raw = self.json_command(
                [*DOCKER, "network", "inspect", "--format", NETWORK_FORMAT, identifier]
            )
            if not raw:
                complete = False
                continue
            ref = alias("network", raw["id"])
            subnets = [r["Subnet"] for r in raw.get("ipam") or [] if r.get("Subnet")]
            ranges.extend(("docker", ref, cidr) for cidr in subnets)
            networks.append(
                {
                    "reference": ref,
                    "driver": raw["driver"],
                    "internal": raw["internal"],
                    "subnet_count": len(subnets),
                }
            )
            self.protected.append(
                {
                    "resource": ref,
                    "reason": "Existing network; no connect/disconnect/create/remove or address changes",
                }
            )
        ok_vol, volume_names, _ = self.reader.command(
            [*DOCKER, "volume", "ls", "-q"], True
        )
        volumes = []
        for name in volume_names.splitlines()[:LIMIT]:
            raw = self.json_command(
                [*DOCKER, "volume", "inspect", "--format", VOLUME_FORMAT, name]
            )
            if raw:
                ref = alias("volume", raw["name"])
                volumes.append({"reference": ref, "driver": raw["driver"]})
                self.protected.append(
                    {
                        "resource": ref,
                        "reason": "Existing data volume; no reads of contents, reuse, prune or removal",
                    }
                )
            else:
                complete = False
        complete = (
            complete
            and ok_net
            and ok_vol
            and len(network_ids.splitlines()) <= LIMIT
            and len(volume_names.splitlines()) <= LIMIT
        )
        version_ok, version, _ = self.reader.command(
            [*DOCKER, "compose", "version", "--short"], True
        )
        summary = {
            "status": "PASS" if complete else "BLOCKED",
            "containers": containers,
            "networks": networks,
            "volumes": volumes,
            "engine_version": info.get("version") if info else None,
            "compose_version": version.strip()
            if version_ok and re.fullmatch(r"v?\d+(?:\.\d+){1,3}[^\s]*\s*", version)
            else None,
        }
        if info and info.get("root"):
            try:
                storage = shutil.disk_usage(info["root"])
                summary["storage"] = {
                    "status": "PASS",
                    "scope": "docker_root",
                    "total_bytes": storage.total,
                    "free_bytes": storage.free,
                }
            except OSError:
                summary["storage"] = {"status": "BLOCKED", "scope": "docker_root"}
        return summary, sockets, ranges, config_roots, complete

    def nginx_inventory(self, extra_roots):
        roots = ["/etc/nginx", "/usr/local/nginx/conf", *extra_roots]
        configs, domains, certificates, seen = [], [], [], set()
        candidates = []
        for root in roots:
            path = Path(root)
            if path.is_file():
                candidates.append(path)
            elif path.is_dir():
                for pattern in (
                    "nginx.conf",
                    "conf.d/*.conf",
                    "sites-enabled/*",
                    "snippets/*.conf",
                    "*.conf",
                ):
                    candidates.extend(path.glob(pattern))
        # Scan known roots, then only explicit file includes. Never invoke nginx -t/-T/-s.
        for _ in range(LIMIT):
            if not candidates:
                break
            path = candidates.pop(0)
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            text = self.reader.config(path)
            if text is None:
                continue
            public, names, certs, includes = nginx_metadata(text)
            configs.append({"reference": alias("config", key), **public})
            domains.extend(names)
            certificates.extend(certs)
            # Only host absolute config paths; container-internal paths cannot be guessed.
            for include in includes:
                if include.startswith("/etc/nginx/") and "$" not in include:
                    candidates.extend(Path(p) for p in glob.glob(include))
        cert_results = []
        for path in sorted(set(certificates))[:LIMIT]:
            if (
                not path.startswith("/")
                or SENSITIVE_PATH.search(path)
                or Path(path).suffix == ".key"
            ):
                continue
            ok, output, _ = self.reader.command(
                [
                    "openssl",
                    "x509",
                    "-in",
                    path,
                    "-noout",
                    "-startdate",
                    "-enddate",
                    "-ext",
                    "subjectAltName",
                ],
                True,
            )
            cert_results.append(
                {
                    "reference": alias("certificate", path),
                    **(
                        certificate_summary(output, domains)
                        if ok
                        else {"status": "BLOCKED"}
                    ),
                }
            )
        nginx_binary = shutil.which("nginx") or "/usr/sbin/nginx"
        ok, out, err = self.reader.command([nginx_binary, "-v"])
        match = re.search(r"nginx/[\d.]+", out + err) if ok else None
        return {
            "status": "UNVERIFIED",
            "binary_version": match[0] if match else None,
            "static_config_scan": configs,
            "public_certificate_metadata": cert_results,
            "runtime_effective_configuration_verified": False,
            "limitations": [
                "Container-baked configuration and unreadable includes require operator review",
                "No nginx -t/-T, no reload, no container exec, no private keys read",
            ],
        }

    def collect(self):
        docker, published, networks, roots, complete = self.docker_inventory()
        ok_ss, sockets, _ = self.reader.command(["ss", "-H", "-lntu"])
        listeners = ports_from_ss(sockets) if ok_ss else []
        port_results = []
        for port in PORTS:
            matches = [row for row in listeners + published if row["port"] == port]
            port_results.append(
                {
                    "port": port,
                    "status": "IN_USE"
                    if matches
                    else "NOT_OBSERVED"
                    if ok_ss and complete
                    else "UNVERIFIED",
                    "bindings": matches,
                    "availability_verified": False,
                }
            )
        ok_route, route_json, _ = self.reader.command(
            ["ip", "-j", "route", "show", "table", "all"]
        )
        routes = []
        if ok_route:
            try:
                routes = [
                    ("route", alias("route", row.get("dev", "")), row["dst"])
                    for row in json.loads(route_json)
                    if row.get("dst") not in {None, "default"}
                ]
            except ValueError:
                ok_route = False
        ok_units, units, _ = self.reader.command(
            [
                "systemctl",
                "list-units",
                "--type=service",
                "--state=running",
                "--no-legend",
                "--no-pager",
                "--plain",
            ]
        )
        host_services = (
            [
                {
                    "reference": alias("unit", line.split()[0]),
                    "kind_hint": family(line.split()[0]),
                }
                for line in units.splitlines()
                if line.split()
            ]
            if ok_units
            else []
        )
        for service in host_services:
            self.protected.append(
                {
                    "resource": service["reference"],
                    "reason": "Existing host service; no stop/restart/reload",
                }
            )
        mem = {}
        try:
            for key, number in re.findall(
                r"^(MemTotal|MemAvailable|SwapTotal|SwapFree):\s+(\d+)",
                Path("/proc/meminfo").read_text(),
                re.MULTILINE,
            ):
                mem[key] = int(number) * 1024
        except OSError:
            pass
        disks = []
        for label, path in (("root", "/"), ("planned_srv_parent", "/srv")):
            try:
                usage = shutil.disk_usage(path)
                disks.append(
                    {
                        "scope": label,
                        "total_bytes": usage.total,
                        "free_bytes": usage.free,
                    }
                )
            except OSError:
                disks.append({"scope": label, "status": "BLOCKED"})
        return {
            "schema_version": 1,
            "target": "operator_selected_existing_test_server",
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "READ_ONLY",
            "host_identity_verified_by_collector": False,
            "resources": {
                "logical_cpus": os.cpu_count(),
                "load_average": list(os.getloadavg()),
                "memory": mem,
                "disks": disks,
                "capacity_approval": "UNVERIFIED",
            },
            "docker": docker,
            "host_services": host_services,
            "port_checks": port_results,
            "network_conflicts": conflict_result(
                CANDIDATE_NETWORK, networks, routes, complete and ok_route
            ),
            "nginx": self.nginx_inventory(roots),
            "do_not_touch": self.protected,
            "ready_for_deployment": "NO",
            "remaining_gates": [
                "Confirm correct server and classify all protected services",
                "Verify complete nginx includes/container mode and live certificates privately",
                "Recheck port/subnet/resource headroom and obtain explicit change approval",
                "Back up and validate recovery before any configuration modification",
            ],
        }


def main():
    parser = argparse.ArgumentParser(
        description="Metadata-only, read-only existing Linux server audit"
    )
    parser.add_argument(
        "--collect", action="store_true", help="Explicitly collect on THIS machine"
    )
    parser.add_argument(
        "--sudo-readonly",
        action="store_true",
        help="Use existing sudo -n authorization for allowlisted metadata reads",
    )
    args = parser.parse_args()
    if not args.collect:
        parser.error(
            "Use --collect only on the intended server via trusted SSH or console"
        )
    try:
        report = Audit(Reader(args.sudo_readonly)).collect()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError):
        print(
            '{"status":"BLOCKED","reason":"audit_metadata_unavailable","ready_for_deployment":"NO"}'
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
