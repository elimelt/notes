import json
from pathlib import Path
import tempfile
import unittest

from scripts.materialize_quartz_lock import make_portable, materialize


class MaterializeQuartzLockTests(unittest.TestCase):
    def test_local_plugins_resolve_relative_to_quartz_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quartz = root / ".quartz"
            quartz.mkdir()
            plugin = root / "quartz-site" / "example"
            plugin.mkdir(parents=True)
            lock_path = quartz / "quartz.lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "plugins": {
                            "example": {
                                "source": "../quartz-site/example",
                                "resolved": "/someone/elses/checkout/example",
                                "commit": "local",
                            },
                            "remote": {
                                "source": "github:owner/plugin",
                                "resolved": "https://github.com/owner/plugin.git",
                                "commit": "abc123",
                            },
                        }
                    }
                )
            )

            materialize(lock_path, quartz)

            lock = json.loads(lock_path.read_text())
            self.assertEqual(
                Path(lock["plugins"]["example"]["resolved"]), plugin.resolve()
            )
            self.assertEqual(
                lock["plugins"]["remote"]["resolved"],
                "https://github.com/owner/plugin.git",
            )

            make_portable(lock_path)
            portable = json.loads(lock_path.read_text())
            self.assertEqual(
                portable["plugins"]["example"]["resolved"],
                "../quartz-site/example",
            )


if __name__ == "__main__":
    unittest.main()
