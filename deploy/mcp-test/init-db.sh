#!/bin/sh
set -eu
# psql receives passwords through the process environment, never argv or echoed SQL.
export MCP_RUNTIME_PASSWORD="$(cat /run/secrets/runtime_password)"
export MCP_MIGRATOR_PASSWORD="$(cat /run/secrets/migrator_password)"
export MCP_OPERATOR_PASSWORD="$(cat /run/secrets/operator_password)"
psql --no-psqlrc --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 <<'SQL'
\getenv runtime_password MCP_RUNTIME_PASSWORD
\getenv migrator_password MCP_MIGRATOR_PASSWORD
\getenv operator_password MCP_OPERATOR_PASSWORD
CREATE ROLE factory_ops_migrator LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'migrator_password';
CREATE ROLE factory_ops_runtime LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 16 PASSWORD :'runtime_password';
CREATE ROLE factory_ops_operator LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'operator_password';
REVOKE ALL ON DATABASE factory_ops_mcp_synthetic FROM PUBLIC;
GRANT CONNECT ON DATABASE factory_ops_mcp_synthetic TO factory_ops_migrator, factory_ops_runtime, factory_ops_operator;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA factory_ops AUTHORIZATION factory_ops_migrator;
GRANT USAGE ON SCHEMA factory_ops TO factory_ops_runtime, factory_ops_operator;
COMMENT ON DATABASE factory_ops_mcp_synthetic IS 'FACTORY_OPS_M1_03B_SYNTHETIC_ONLY';
ALTER ROLE factory_ops_runtime IN DATABASE factory_ops_mcp_synthetic SET search_path=factory_ops,pg_catalog;
ALTER ROLE factory_ops_operator IN DATABASE factory_ops_mcp_synthetic SET search_path=factory_ops,pg_catalog;
ALTER ROLE factory_ops_migrator IN DATABASE factory_ops_mcp_synthetic SET search_path=factory_ops,pg_catalog;
ALTER ROLE factory_ops_runtime SET statement_timeout='5s';
ALTER ROLE factory_ops_runtime SET lock_timeout='2s';
ALTER ROLE factory_ops_runtime SET idle_in_transaction_session_timeout='10s';
ALTER ROLE factory_ops_operator SET statement_timeout='10s';
SQL
unset MCP_RUNTIME_PASSWORD MCP_MIGRATOR_PASSWORD MCP_OPERATOR_PASSWORD
