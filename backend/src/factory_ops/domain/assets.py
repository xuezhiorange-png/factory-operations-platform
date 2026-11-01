"""Minimum asset read model; no equipment control or mutable workflow."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Factory:
    id: UUID
    code: str
    name: str


@dataclass(frozen=True)
class Asset:
    id: UUID
    factory_id: UUID
    asset_code: str
    name: str
    category: str
    location: str | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AssetPage:
    items: tuple[Asset, ...]
    total: int
    limit: int
    offset: int
