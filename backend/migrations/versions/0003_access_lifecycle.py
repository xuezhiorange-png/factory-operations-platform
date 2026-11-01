"""M1-02B: single-factory admins, monotonic authorization epochs and access audit."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_access_lifecycle"
down_revision = "0002_feishu_sessions"
branch_labels = depends_on = None


def upgrade():
    op.add_column("audit_events", sa.Column("details", JSONB(), nullable=True))
    op.create_check_constraint("ck_user_versions", "users", "auth_version >= 1 AND version >= 1")
    op.create_check_constraint("ck_session_auth_version", "auth_sessions", "auth_version >= 1")
    # Existing inconsistent scopes require explicit correction; never trim them silently.
    op.execute("""DO $$ BEGIN IF EXISTS (
        SELECT 1 FROM users u JOIN user_factory_access a ON u.id=a.user_id
        WHERE u.role='factory_equipment_admin' GROUP BY u.id HAVING count(*)>1
    ) THEN RAISE EXCEPTION 'inconsistent factory administrator scope'; END IF; END $$""")
    op.execute("""CREATE FUNCTION version_account_changes() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.auth_version < OLD.auth_version OR NEW.version < OLD.version THEN
        RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='account versions cannot decrease';
      END IF;
      IF (NEW.role, NEW.active) IS DISTINCT FROM (OLD.role, OLD.active) THEN
        NEW.auth_version := greatest(NEW.auth_version, OLD.auth_version+1);
        NEW.version := greatest(NEW.version, OLD.version+1);
      ELSIF NEW.auth_version > OLD.auth_version
        OR NEW.display_name IS DISTINCT FROM OLD.display_name THEN
        NEW.version := greatest(NEW.version, OLD.version+1);
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("""CREATE TRIGGER version_account_changes BEFORE UPDATE ON users
      FOR EACH ROW EXECUTE FUNCTION version_account_changes()""")
    op.execute("""CREATE FUNCTION revoke_changed_account_sessions() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.auth_version IS DISTINCT FROM OLD.auth_version THEN
        UPDATE auth_sessions SET revoked_at=now() WHERE user_id=NEW.id AND revoked_at IS NULL;
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("""CREATE TRIGGER revoke_changed_account_sessions AFTER UPDATE ON users
      FOR EACH ROW EXECUTE FUNCTION revoke_changed_account_sessions()""")
    op.execute("""CREATE FUNCTION invalidate_scope_change() RETURNS trigger
    LANGUAGE plpgsql AS $$
    DECLARE target uuid;
    BEGIN
      IF TG_OP='UPDATE' AND (NEW.user_id,NEW.factory_id)
        IS NOT DISTINCT FROM (OLD.user_id,OLD.factory_id) THEN RETURN NEW; END IF;
      FOR target IN SELECT DISTINCT value FROM unnest(ARRAY[
        CASE WHEN TG_OP<>'INSERT' THEN OLD.user_id ELSE NULL END,
        CASE WHEN TG_OP<>'DELETE' THEN NEW.user_id ELSE NULL END
      ]) value WHERE value IS NOT NULL ORDER BY value LOOP
        PERFORM 1 FROM users WHERE id=target FOR UPDATE;
        UPDATE users SET auth_version=auth_version+1,version=version+1 WHERE id=target;
      END LOOP;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$""")
    op.execute("""CREATE TRIGGER invalidate_scope_change BEFORE INSERT OR UPDATE OR DELETE
      ON user_factory_access FOR EACH ROW EXECUTE FUNCTION invalidate_scope_change()""")
    op.execute("""CREATE FUNCTION enforce_single_factory_admin() RETURNS trigger
    LANGUAGE plpgsql AS $$
    DECLARE target uuid; management_role_value text;
    BEGIN
      IF TG_TABLE_NAME='users' THEN target:=NEW.id;
      ELSIF TG_OP='DELETE' THEN target:=OLD.user_id;
      ELSE target:=NEW.user_id; END IF;
      SELECT role INTO management_role_value FROM users WHERE id=target FOR UPDATE;
      IF management_role_value='factory_equipment_admin' AND
         (SELECT count(*) FROM user_factory_access WHERE user_id=target)>1 THEN
        RAISE EXCEPTION USING ERRCODE='23514',
          MESSAGE='factory administrators have at most one factory';
      END IF;
      RETURN NULL;
    END $$""")
    op.execute("""CREATE CONSTRAINT TRIGGER check_admin_scope AFTER INSERT OR UPDATE OR DELETE
      ON user_factory_access DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
      EXECUTE FUNCTION enforce_single_factory_admin()""")
    op.execute("""CREATE CONSTRAINT TRIGGER check_admin_role AFTER INSERT OR UPDATE ON users
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION enforce_single_factory_admin()""")
    op.execute("""CREATE FUNCTION invalidate_identity_change() RETURNS trigger
    LANGUAGE plpgsql AS $$
    DECLARE target uuid;
    BEGIN
      IF TG_OP='UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
      FOR target IN SELECT DISTINCT value FROM unnest(ARRAY[OLD.user_id,
        CASE WHEN TG_OP='UPDATE' THEN NEW.user_id ELSE NULL END
      ]) value WHERE value IS NOT NULL ORDER BY value LOOP
        UPDATE users SET auth_version=auth_version+1,version=version+1 WHERE id=target;
      END LOOP;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$""")
    op.execute("""CREATE TRIGGER invalidate_identity_change AFTER UPDATE OR DELETE
      ON external_identities FOR EACH ROW EXECUTE FUNCTION invalidate_identity_change()""")


def downgrade():
    # Never erase populated forensic details to make an application rollback convenient.
    op.execute("""DO $$ BEGIN IF EXISTS (
      SELECT 1 FROM audit_events WHERE details IS NOT NULL
    ) THEN RAISE EXCEPTION 'preserve access audit facts; retain schema and roll back code';
      END IF; END $$""")
    op.execute("UPDATE auth_sessions SET revoked_at=now() WHERE revoked_at IS NULL")
    for trigger, table in [
        ("invalidate_identity_change", "external_identities"),
        ("check_admin_role", "users"),
        ("check_admin_scope", "user_factory_access"),
        ("invalidate_scope_change", "user_factory_access"),
        ("revoke_changed_account_sessions", "users"),
        ("version_account_changes", "users"),
    ]:
        op.execute(f"DROP TRIGGER {trigger} ON {table}")
    for name in [
        "invalidate_identity_change",
        "enforce_single_factory_admin",
        "invalidate_scope_change",
        "revoke_changed_account_sessions",
        "version_account_changes",
    ]:
        op.execute(f"DROP FUNCTION {name}()")
    op.drop_constraint("ck_session_auth_version", "auth_sessions", type_="check")
    op.drop_constraint("ck_user_versions", "users", type_="check")
    op.drop_column("audit_events", "details")
