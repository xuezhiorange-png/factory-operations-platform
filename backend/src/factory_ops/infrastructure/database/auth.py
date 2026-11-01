"""Persistence adapter for one-time OAuth, verified bindings and platform sessions."""

import hmac
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError

from factory_ops.application.auth import AccountView, digest, valid_opaque
from factory_ops.application.errors import AccessDenied, CsrfRejected, InvalidLogin, SessionExpired
from factory_ops.application.identity import ExternalIdentity, SessionIdentity
from factory_ops.infrastructure.database.models import (
    ExternalIdentityRow,
    OAuthFlowRow,
    SessionRow,
    UserRow,
)
from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork


class SqlAuthUnitOfWork(SqlReadUnitOfWork):
    def lock_lifecycle(self):
        # Shared by login, offline bootstrap and access mutations to order account/binding locks.
        self.session.execute(text("SELECT pg_advisory_xact_lock(742102001)"))

    def add_flow(self, state, browser, destination, channel, expires):
        self.session.add(
            OAuthFlowRow(
                state_hash=state,
                browser_hash=browser,
                return_to=destination,
                channel=channel,
                expires_at=expires,
            )
        )

    def consume_flow(self, state, browser, code, now):
        flow = self.session.scalar(
            select(OAuthFlowRow).where(OAuthFlowRow.state_hash == state).with_for_update()
        )
        if (
            flow is None
            or flow.consumed_at is not None
            or flow.expires_at <= now
            or not hmac.compare_digest(flow.browser_hash, browser)
        ):
            raise InvalidLogin
        flow.consumed_at, flow.code_hash = now, code
        try:
            self.session.flush()
        except IntegrityError:
            raise InvalidLogin from None
        return flow.return_to

    def bind_and_issue(self, identity: ExternalIdentity, token_hash, csrf_hash, lifetime, previous):
        self.lock_lifecycle()
        # Serialize first-seen bindings across callbacks; never infer identity from profile data.
        key = digest(
            "|".join(
                [
                    identity.provider,
                    identity.issuer,
                    identity.tenant_id,
                    identity.app_id,
                    identity.subject_id,
                ]
            )
        )
        self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(key[:15], 16)})
        binding = self.session.scalar(
            select(ExternalIdentityRow)
            .where(
                ExternalIdentityRow.provider == identity.provider,
                ExternalIdentityRow.issuer == identity.issuer,
                ExternalIdentityRow.tenant_id == identity.tenant_id,
                ExternalIdentityRow.app_id == identity.app_id,
                ExternalIdentityRow.subject_id == identity.subject_id,
            )
            .with_for_update()
        )
        if binding is None:
            user = UserRow(role=None, display_name=identity.display_name)
            self.session.add(user)
            self.session.flush()
            binding = ExternalIdentityRow(
                user_id=user.id,
                provider=identity.provider,
                issuer=identity.issuer,
                tenant_id=identity.tenant_id,
                app_id=identity.app_id,
                subject_id=identity.subject_id,
            )
            self.session.add(binding)
            self.session.flush()
            self.audit(user.id, None, user.id, "identity.first_seen", "allowed", "api")
        else:
            user = self.session.scalar(
                select(UserRow).where(UserRow.id == binding.user_id).with_for_update()
            )
        if not binding.active or not user.active:
            self.audit(user.id, None, user.id, "auth.login", "denied", "api")
            self.commit()
            raise AccessDenied
        if previous:
            self.session.execute(
                update(SessionRow)
                .where(SessionRow.token_hash == previous, SessionRow.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )
        self.session.add(
            SessionRow(
                user_id=user.id,
                external_identity_id=binding.id,
                token_hash=token_hash,
                csrf_hash=csrf_hash,
                auth_version=user.auth_version,
                expires_at=datetime.now(UTC) + timedelta(seconds=lifetime),
            )
        )
        self.audit(user.id, None, user.id, "auth.login", "allowed", "api")

    def session_record(self, token):
        if not valid_opaque(token):
            raise SessionExpired
        uid = self.resolve_identity(SessionIdentity(digest(token)))
        if uid is None:
            raise SessionExpired
        record = self.session.scalar(
            select(SessionRow).where(SessionRow.token_hash == digest(token))
        )
        return record

    def account(self, token):
        record = self.session_record(token)
        user = self.session.get(UserRow, record.user_id)
        principal = self.load_principal(user.id)
        factories = self.factories(principal) if principal is not None else ()
        return AccountView(
            user.id,
            user.display_name or "账号 " + str(user.id)[:8],
            user.role,
            "authorized" if principal and (factories or user.role == "group_lead") else "pending",
            factories,
        )

    def require_csrf(self, token, csrf):
        record = self.session_record(token)
        if (
            not valid_opaque(csrf)
            or not record.csrf_hash
            or not hmac.compare_digest(record.csrf_hash, digest(csrf))
        ):
            raise CsrfRejected
        return record

    def revoke_session(self, token):
        record = self.session_record(token)
        record.revoked_at = datetime.now(UTC)
        self.audit(record.user_id, None, record.id, "auth.logout", "allowed", "api")
