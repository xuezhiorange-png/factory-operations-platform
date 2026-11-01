"""SQLAlchemy 2 mappings. Schema changes are owned by Alembic migrations."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class FactoryRow(Base):
    __tablename__ = "factories"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IS NULL OR role IN ('group_lead', 'engineer', 'factory_equipment_admin')",
            name="ck_users_management_role",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # No name/phone/email is needed by the minimum read capability.
    role: Mapped[str | None] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    display_name: Mapped[str | None] = mapped_column(String(200))
    auth_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class FactoryAccessRow(Base):
    __tablename__ = "user_factory_access"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    factory_id: Mapped[UUID] = mapped_column(
        ForeignKey("factories.id", ondelete="RESTRICT"), primary_key=True
    )


class ExternalIdentityRow(Base):
    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider", "issuer", "tenant_id", "app_id", "subject_id", name="uq_external_identity"
        ),
        CheckConstraint("provider IN ('feishu', 'doubao_mcp')", name="ck_identity_provider"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    provider: Mapped[str] = mapped_column(String(32))
    issuer: Mapped[str] = mapped_column(String(200))
    tenant_id: Mapped[str] = mapped_column(String(200))
    app_id: Mapped[str] = mapped_column(String(200))
    subject_id: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SessionRow(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (CheckConstraint("expires_at > issued_at", name="ck_session_expiry"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auth_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    external_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("external_identities.id", ondelete="RESTRICT")
    )
    csrf_hash: Mapped[str | None] = mapped_column(String(64))


class OAuthFlowRow(Base):
    __tablename__ = "oauth_flows"
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    browser_hash: Mapped[str] = mapped_column(String(64))
    code_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    return_to: Mapped[str] = mapped_column(String(600))
    channel: Mapped[str] = mapped_column(String(8))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssetRow(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("factory_id", "asset_code", name="uq_asset_factory_code"),
        CheckConstraint(
            "length(trim(asset_code)) > 0 AND length(trim(name)) > 0", name="ck_asset_required"
        ),
        CheckConstraint(
            "category IN ('refrigeration','processing','utilities','other')",
            name="ck_asset_category",
        ),
        CheckConstraint(
            "status IN ('pending','in_use','inactive','retired')", name="ck_asset_status"
        ),
        CheckConstraint("version >= 1", name="ck_asset_version"),
        Index("ix_assets_factory_code_id", "factory_id", "asset_code", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    factory_id: Mapped[UUID] = mapped_column(ForeignKey("factories.id", ondelete="RESTRICT"))
    asset_code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(32))
    location: Mapped[str | None] = mapped_column(String(300))
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    model: Mapped[str | None] = mapped_column(String(200))
    serial_number: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditRow(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("outcome IN ('allowed','denied')", name="ck_audit_outcome"),
        CheckConstraint("channel IN ('api','doubao_mcp')", name="ck_audit_channel"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    # Requested identifiers can be nonexistent/unauthorized; deliberately not business FKs.
    factory_id: Mapped[UUID | None]
    resource_id: Mapped[UUID | None]
    action: Mapped[str] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(16))
    channel: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
