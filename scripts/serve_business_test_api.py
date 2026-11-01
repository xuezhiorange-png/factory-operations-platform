"""Loopback-only synthetic browser fixture. No login endpoint or tokens in logs/artifacts."""

import json
import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "tests"))

from db_support import isolated_database, seed_synthetic
from factory_ops.api.app import create_app
from factory_ops.application.assets import AssetQueries
from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork


def main() -> None:
    credential_file = Path(os.environ["FACTORY_OPS_BROWSER_AUTH_FILE"]).resolve()
    if credential_file.is_relative_to(ROOT) or not credential_file.parent.is_dir():
        raise RuntimeError(
            "Browser credentials must be kept outside checkout and artifact directories"
        )
    database = isolated_database()
    try:
        data = seed_synthetic(database.engine)
        descriptor = {
            "factories": {k: str(v) for k, v in data.factories.items()},
            "assets": {k: str(v) for k, v in data.assets.items()},
            "tokens": data.tokens,
        }
        fd = os.open(credential_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(descriptor, output)
        app = create_app(
            lambda: AssetQueries(lambda: SqlReadUnitOfWork(database.engine)),
            data_source="synthetic_test",
        )
        uvicorn.run(
            app, host="127.0.0.1", port=8011, access_log=False, log_level="warning"
        )
    finally:
        credential_file.unlink(missing_ok=True)
        database.cleanup()


if __name__ == "__main__":
    main()
