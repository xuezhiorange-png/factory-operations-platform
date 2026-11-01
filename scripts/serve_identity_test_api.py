"""HTTPS browser fixture with synthetic Feishu HTTP transport; no bypass/login endpoints."""

import json
import os
import secrets
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "tests"))

from db_support import isolated_database, seed_synthetic
from feishu_support import auth_fixture


def main():
    output = Path(os.environ["FACTORY_OPS_IDENTITY_FIXTURE"]).resolve()
    if output.is_relative_to(ROOT) or not output.parent.is_dir():
        raise RuntimeError("Private identity fixture must be outside checkout")
    db = isolated_database()
    try:
        data = seed_synthetic(db.engine)
        app, _, codes, subjects = auth_fixture(db, data, "https://localhost:4175")
        subjects["pending"] = "SYNTH-FIRST-LOGIN"
        subjects["lifecycle"] = "SYNTH-ONLY-LIFECYCLE"
        pool = {}
        for role, subject in subjects.items():
            pool[role] = []
            for _ in range(40):
                code = secrets.token_urlsafe(32)
                codes[code] = subject
                pool[role].append(code)
        fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(
                {
                    "factories": {k: str(v) for k, v in data.factories.items()},
                    "assets": {k: str(v) for k, v in data.assets.items()},
                    "users": {k: str(v) for k, v in data.users.items()},
                    "codes": pool,
                },
                handle,
            )
        uvicorn.run(
            app, host="127.0.0.1", port=8012, access_log=False, log_level="warning"
        )
    finally:
        output.unlink(missing_ok=True)
        db.cleanup()


if __name__ == "__main__":
    main()
