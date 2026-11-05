import json
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ca.store import RunStore, test_set_version
from ca.version import GENERATOR_VERSION


class RunStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "runs"
        self.store = RunStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def begin(self):
        return self.store.begin(
            {
                "writer_model": "写作模型",
                "brand_hash": "brand",
                "client_store_hash": "clients",
                "test_set_version": "tests",
                "split": "tuning",
                "case_ids": ["c1"],
            }
        )

    def test_begin_writes_versioned_manifest_once(self):
        run_id = self.begin()
        run_dir = self.root / GENERATOR_VERSION / run_id
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertRegex(run_id, r"^\d{8}T\d{9}Z$")
        self.assertEqual(manifest["generator_version"], GENERATOR_VERSION)
        self.assertEqual(manifest["writer_model"], "写作模型")
        self.assertEqual(manifest["brand_hash"], "brand")
        self.assertEqual(manifest["client_store_hash"], "clients")
        self.assertEqual(manifest["test_set_version"], "tests")
        self.assertEqual(manifest["split"], "tuning")
        self.assertEqual(manifest["case_ids"], ["c1"])
        self.assertIn("start", manifest)
        self.assertNotIn("end", manifest)
        self.assertIn("写作模型", (run_dir / "manifest.json").read_text(encoding="utf-8"))

    def test_begin_uses_the_next_millisecond_on_collision(self):
        instant = datetime(2026, 11, 4, 23, 15, 1, 123000, tzinfo=timezone.utc)
        with patch("ca.store.datetime") as clock:
            clock.now.return_value = instant
            first = self.begin()
            second = self.begin()
        self.assertEqual(first, "20261104T231501123Z")
        self.assertEqual(second, "20261104T231501124Z")

    def test_write_case_and_finish_manifest_refuse_rewrites(self):
        run_id = self.begin()
        self.store.write_case(run_id, "c1", {"text": "您好"})
        with self.assertRaises(FileExistsError):
            self.store.write_case(run_id, "c1", {"text": "再见"})

        self.store.finish_manifest(run_id, {"end": "2026-11-04T20:00:00Z"})
        with self.assertRaises(FileExistsError):
            self.store.finish_manifest(run_id, {"end": "later"})

        run_dir = self.root / GENERATOR_VERSION / run_id
        self.assertFalse("end" in json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")))
        self.assertEqual(
            json.loads((run_dir / "manifest.end.json").read_text(encoding="utf-8"))["end"],
            "2026-11-04T20:00:00Z",
        )

    def test_parallel_appends_produce_complete_json_lines(self):
        run_id = self.begin()

        def append(start):
            for number in range(start, start + 10):
                self.store.append(run_id, "events.jsonl", {"number": number, "text": "中文"})

        threads = [threading.Thread(target=append, args=(start,)) for start in (0, 10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        path = self.root / GENERATOR_VERSION / run_id / "events.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 20)
        self.assertEqual({row["number"] for row in rows}, set(range(20)))
        self.assertTrue(all(row["text"] == "中文" for row in rows))

    def test_test_set_version_hashes_both_files_and_profiles(self):
        inputs = Path(self.temp.name) / "inputs.jsonl"
        tuning = Path(self.temp.name) / "tuning.jsonl"
        inputs.write_bytes(b'{"case_id":"f1"}\n')
        tuning.write_bytes(b'{"case_id":"t1"}\n')
        profiles = [{"id": "lin", "name": "林女士"}]
        original = test_set_version(inputs, tuning, profiles)

        inputs.write_bytes(b'{"case_id":"f2"}\n')
        self.assertNotEqual(original, test_set_version(inputs, tuning, profiles))
        inputs.write_bytes(b'{"case_id":"f1"}\n')
        tuning.write_bytes(b'{"case_id":"t2"}\n')
        self.assertNotEqual(original, test_set_version(inputs, tuning, profiles))
        tuning.write_bytes(b'{"case_id":"t1"}\n')
        self.assertNotEqual(
            original,
            test_set_version(inputs, tuning, [{"id": "lin", "name": "林小姐"}]),
        )


if __name__ == "__main__":
    unittest.main()
