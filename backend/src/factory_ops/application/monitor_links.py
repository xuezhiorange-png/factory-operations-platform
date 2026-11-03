"""Explicit reviewed ID associations. Never match names or read the monitor database."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


@dataclass(frozen=True)
class MonitorLink:
    factory_id: UUID
    asset_id: UUID
    monitor_factory_id: str
    monitor_gateway_id: str
    monitor_device_id: str
    valid_from: datetime
    valid_to: datetime | None = None

    def active(self, now: datetime) -> bool:
        return self.valid_from <= now and (self.valid_to is None or now < self.valid_to)


def parse_monitor_links(raw: str) -> tuple[MonitorLink, ...]:
    """Trusted deployment configuration only; malformed/ambiguous maps block startup."""
    try:
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) > 1000:
            raise ValueError
        links = []
        required = {
            "factory_id",
            "asset_id",
            "monitor_factory_id",
            "monitor_gateway_id",
            "monitor_device_id",
            "valid_from",
        }
        for row in rows:
            if not isinstance(row, dict) or set(row) - required - {"valid_to"}:
                raise ValueError
            if not required <= set(row):
                raise ValueError
            if not re.fullmatch(r"FAC_[A-Z0-9_]{1,100}", row["monitor_factory_id"]):
                raise ValueError
            if not re.fullmatch(r"[0-9]{1,20}", row["monitor_gateway_id"]):
                raise ValueError
            if not re.fullmatch(r"[A-Za-z0-9_:-]{1,200}", row["monitor_device_id"]):
                raise ValueError
            start = datetime.fromisoformat(row["valid_from"])
            end = datetime.fromisoformat(row["valid_to"]) if row.get("valid_to") else None
            if start.tzinfo is None or (end and (end.tzinfo is None or end <= start)):
                raise ValueError
            link = MonitorLink(
                UUID(row["factory_id"]),
                UUID(row["asset_id"]),
                row["monitor_factory_id"],
                row["monitor_gateway_id"],
                row["monitor_device_id"],
                start,
                end,
            )
            for previous in links:
                same_asset = (link.factory_id, link.asset_id) == (
                    previous.factory_id,
                    previous.asset_id,
                )
                same_device = (link.monitor_factory_id, link.monitor_device_id) == (
                    previous.monitor_factory_id,
                    previous.monitor_device_id,
                )
                overlap = (previous.valid_to is None or start < previous.valid_to) and (
                    end is None or previous.valid_from < end
                )
                if overlap and (same_asset or same_device):
                    raise ValueError
                if link.monitor_factory_id == previous.monitor_factory_id and (
                    link.factory_id != previous.factory_id
                ):
                    raise ValueError
                if link.monitor_gateway_id == previous.monitor_gateway_id and (
                    link.monitor_factory_id != previous.monitor_factory_id
                ):
                    raise ValueError
            links.append(link)
        return tuple(links)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError("Invalid explicit monitor ID mapping configuration") from None


def current_links(links: tuple[MonitorLink, ...]) -> tuple[MonitorLink, ...]:
    now = datetime.now(UTC)
    return tuple(link for link in links if link.active(now))
