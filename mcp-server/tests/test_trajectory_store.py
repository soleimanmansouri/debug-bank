"""Two records saved in the same second must both survive (they used to overwrite)."""
import tempfile
import unittest
from pathlib import Path

from debug_bank_mcp.memory.trajectory_store import TrajectoryStore


class TrajectoryStoreTest(unittest.TestCase):
    def test_same_second_records_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            store = TrajectoryStore(Path(d))
            ids = {store.save({"pattern_id": "novel", "symptom": f"s{i}"}) for i in range(5)}
            self.assertEqual(len(ids), 5)
            self.assertEqual(len(list(Path(d).glob("*.json"))), 5)


if __name__ == "__main__":
    unittest.main()
