"""Config generation helpers for the challenge PHP app."""

from __future__ import annotations

import os
from pathlib import Path

from math_tutor.env_config import load_dotenv_if_present


def generate_config_php(output_path: Path) -> None:
    load_dotenv_if_present()
    host = os.environ.get("MYSQL_HOST") or os.environ.get("MySQL_HOST") or "localhost"
    dbname = os.environ.get("DBNAME", "")
    user = os.environ.get("DBUSER", "")
    password = os.environ.get("DBPASSWORD", "")
    output_path.write_text(
        f"<?php\n"
        f"define('DB_HOST', {_php_str(host)});\n"
        f"define('DB_NAME', {_php_str(dbname)});\n"
        f"define('DB_USER', {_php_str(user)});\n"
        f"define('DB_PASS', {_php_str(password)});\n",
        encoding="utf-8",
    )


def _php_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"
