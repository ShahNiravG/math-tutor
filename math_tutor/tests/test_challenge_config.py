from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from math_tutor.challenge_config import generate_config_php


class ChallengeConfigTests(unittest.TestCase):
    def test_generate_config_php_writes_expected_php_constants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "config.php"
            env = {
                **os.environ,
                "MYSQL_HOST": "db.example.com",
                "DBNAME": "mathdelight",
                "DBUSER": "student_user",
                "DBPASSWORD": "secret-pass",
            }
            with patch.dict(os.environ, env, clear=True):
                generate_config_php(output_path)

            text = output_path.read_text(encoding="utf-8")
            self.assertIn("define('DB_HOST', 'db.example.com');", text)
            self.assertIn("define('DB_NAME', 'mathdelight');", text)
            self.assertIn("define('DB_USER', 'student_user');", text)
            self.assertIn("define('DB_PASS', 'secret-pass');", text)


if __name__ == "__main__":
    unittest.main()
