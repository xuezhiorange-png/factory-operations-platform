"""Factory isolation and independent acceptance at the pure-policy boundary only."""

from uuid import UUID

import pytest

from factory_ops.domain.authorization import (
    ManagementRole,
    Principal,
    can_access_factory,
    can_manage_access,
    can_verify_work_order,
)

A = UUID("10000000-0000-4000-8000-000000000001")
B = UUID("10000000-0000-4000-8000-000000000002")
USER_1 = UUID("20000000-0000-4000-8000-000000000001")
USER_2 = UUID("20000000-0000-4000-8000-000000000002")
USER_3 = UUID("20000000-0000-4000-8000-000000000003")


def test_exactly_three_management_roles() -> None:
    assert {role.value for role in ManagementRole} == {
        "group_lead", "engineer", "factory_equipment_admin"
    }


@pytest.mark.parametrize(
    ("role", "grants", "expected_a", "expected_b"),
    [
        (ManagementRole.GROUP_LEAD, frozenset(), True, True),
        (ManagementRole.ENGINEER, frozenset({A}), True, False),
        (ManagementRole.ENGINEER, frozenset({A, B}), True, True),
        (ManagementRole.ENGINEER, frozenset(), False, False),
        (ManagementRole.FACTORY_EQUIPMENT_ADMIN, frozenset({B}), False, True),
        (ManagementRole.FACTORY_EQUIPMENT_ADMIN, frozenset(), False, False),
    ],
)
def test_factory_access_matrix(
    role: ManagementRole, grants: frozenset[UUID], expected_a: bool, expected_b: bool
) -> None:
    principal = Principal(USER_1, role, grants)
    assert can_access_factory(principal, A) is expected_a
    assert can_access_factory(principal, B) is expected_b


def test_factory_admin_cannot_hold_multiple_factory_grants() -> None:
    with pytest.raises(ValueError, match="at most one factory"):
        Principal(USER_1, ManagementRole.FACTORY_EQUIPMENT_ADMIN, frozenset({A, B}))


def test_unknown_management_role_cannot_gain_access_via_factory_grants() -> None:
    with pytest.raises(ValueError, match="Unknown management role"):
        Principal(USER_1, "unexpected_role", frozenset({A}))  # type: ignore[arg-type]


def test_factory_grants_cannot_change_through_a_mutable_collection() -> None:
    with pytest.raises(ValueError, match="immutable snapshot"):
        Principal(USER_1, ManagementRole.ENGINEER, {A})  # type: ignore[arg-type]


@pytest.mark.parametrize("role", ManagementRole)
def test_only_group_lead_can_manage_roles_and_grants(role: ManagementRole) -> None:
    assert can_manage_access(Principal(USER_1, role, frozenset({A}))) is (
        role is ManagementRole.GROUP_LEAD
    )


@pytest.mark.parametrize("role", ManagementRole)
def test_all_actual_repairers_cannot_self_verify_even_if_group_lead(role: ManagementRole) -> None:
    principal = Principal(USER_1, role, frozenset({A}))
    assert not can_verify_work_order(
        principal,
        factory_id=A,
        actual_repairer_user_ids=frozenset({USER_2, USER_1}),
        awaiting_verification=True,
    )


@pytest.mark.parametrize("role", ManagementRole)
def test_independent_authorized_person_can_verify(role: ManagementRole) -> None:
    principal = Principal(USER_3, role, frozenset({A}))
    assert can_verify_work_order(
        principal,
        factory_id=A,
        actual_repairer_user_ids=frozenset({USER_1, USER_2}),
        awaiting_verification=True,
    )


@pytest.mark.parametrize("role", [ManagementRole.ENGINEER, ManagementRole.FACTORY_EQUIPMENT_ADMIN])
def test_cross_factory_verification_denied(role: ManagementRole) -> None:
    assert not can_verify_work_order(
        Principal(USER_3, role, frozenset({B})),
        factory_id=A,
        actual_repairer_user_ids=frozenset({USER_1}),
        awaiting_verification=True,
    )


@pytest.mark.parametrize("role", ManagementRole)
def test_acceptance_outside_pending_verification_state_denied(role: ManagementRole) -> None:
    assert not can_verify_work_order(
        Principal(USER_3, role, frozenset({A})),
        factory_id=A,
        actual_repairer_user_ids=frozenset({USER_1}),
        awaiting_verification=False,
    )


def test_missing_actual_repairer_evidence_denies_verification() -> None:
    assert not can_verify_work_order(
        Principal(USER_3, ManagementRole.GROUP_LEAD),
        factory_id=A,
        actual_repairer_user_ids=frozenset(),
        awaiting_verification=True,
    )
