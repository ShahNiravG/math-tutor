from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.env_config import load_dotenv_if_present


class EnvConfigTests(unittest.TestCase):
    def test_load_dotenv_if_present_loads_missing_variables_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                'OPENAI_API_KEY="loaded-key"\nEXISTING_VAR=from-file\n',
                encoding="utf-8",
            )

            original_openai = os.environ.pop("OPENAI_API_KEY", None)
            original_existing = os.environ.get("EXISTING_VAR")
            os.environ["EXISTING_VAR"] = "keep-existing"
            try:
                load_dotenv_if_present(env_path)
                self.assertEqual(os.environ.get("OPENAI_API_KEY"), "loaded-key")
                self.assertEqual(os.environ.get("EXISTING_VAR"), "keep-existing")
            finally:
                if original_openai is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = original_openai
                if original_existing is None:
                    os.environ.pop("EXISTING_VAR", None)
                else:
                    os.environ["EXISTING_VAR"] = original_existing


if __name__ == "__main__":
    unittest.main()
