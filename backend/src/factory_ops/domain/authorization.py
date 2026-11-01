"""Minimal *pure* role-and-factory policy examples.

M0 does NOT provide authentication or server-side endpoint authorization.
These policies are preparation for M1; using them alone is NOT sufficient to secure APIs.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ManagementRole(StrEnum):
    GROUP_LEAD = "group_lead"
    ENGINEER = "engineer"
    FACTORY_EQUIPMENT_ADMIN = "factory_equipment_admin"


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    role: ManagementRole
    factory_ids: frozenset[UUID] = frozenset()

    def __post_init__(self) -> None:
        # This is a trusted domain value, never a substitute for authenticating a request.
        if not isinstance(self.role, ManagementRole):
            raise ValueError("Unknown management role")
        if not isinstance(self.factory_ids, frozenset):
            raise ValueError("Factory grants must be an immutable snapshot")
        if self.role is ManagementRole.FACTORY_EQUIPMENT_ADMIN and len(self.factory_ids) > 1:
            raise ValueError("A factory equipment admin may be granted at most one factory")


def can_access_factory(principal: Principal, factory_id: UUID) -> bool:
    """Group lead sees all; all other management roles require explicit factory grants."""
    return principal.role is ManagementRole.GROUP_LEAD or factory_id in principal.factory_ids


def can_manage_access(principal: Principal) -> bool:
    """Only the group lead may manage roles and factory grants."""
    return principal.role is ManagementRole.GROUP_LEAD


def can_verify_work_order(
    principal: Principal,
    *,
    factory_id: UUID,
    actual_repairer_user_ids: frozenset[UUID],
    awaiting_verification: bool,
) -> bool:
    """Require pending acceptance, known repairers and an independent authorized verifier.

    The application must load all context from the persisted work order, not request fields.
    M0 has no work-order state machine, authentication, revocation or write endpoint.
    """
    return (
        awaiting_verification
        and bool(actual_repairer_user_ids)
        and can_access_factory(principal, factory_id)
        and principal.user_id not in actual_repairer_user_ids
    )
