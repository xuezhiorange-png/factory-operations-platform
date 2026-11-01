"""M1-02A: OAuth challenges, bound platform sessions and account versioning."""

import sqlalchemy as sa
from alembic import op

revision = "0002_feishu_sessions"
down_revision = "0001_m1_foundation"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("display_name", sa.String(200), nullable=True))
    for name in ("auth_version", "version"):
        op.add_column("users", sa.Column(name, sa.Integer(), nullable=False, server_default="1"))
    op.add_column(
        "auth_sessions", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column("auth_sessions", sa.Column("csrf_hash", sa.String(64), nullable=True))
    op.add_column("auth_sessions", sa.Column("external_identity_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_session_external_identity",
        "auth_sessions",
        "external_identities",
        ["external_identity_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "oauth_flows",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("code_hash", sa.String(64), unique=True, nullable=True),
        sa.Column("return_to", sa.String(600), nullable=False),
        sa.Column("channel", sa.String(8), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    # An older application cannot enforce binding/version checks: invalidate issued sessions first.
    op.execute("UPDATE auth_sessions SET revoked_at = now() WHERE revoked_at IS NULL")
    op.drop_table("oauth_flows")
    op.drop_constraint("fk_session_external_identity", "auth_sessions", type_="foreignkey")
    for name in ("external_identity_id", "csrf_hash", "auth_version"):
        op.drop_column("auth_sessions", name)
    for name in ("version", "auth_version", "display_name"):
        op.drop_column("users", name)
