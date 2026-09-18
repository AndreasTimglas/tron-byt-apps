import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from server import Store
from scheduling import parse_local


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "message.json"
        self.store = Store(self.path)
        self.now = parse_local("2026-09-18T10:00")
        self.clock = patch("server.time.time", return_value=self.now)
        self.mock_time = self.clock.start()
        self.payload = {"text": "Lunch at noon", "color": "green", "start": "2026-09-18T12:00", "end": "2026-09-18T15:00"}

    def tearDown(self):
        self.clock.stop()
        self.temp.cleanup()

    def test_boundaries_restart_and_offline_window(self):
        self.store.schedule(self.payload)
        self.assertFalse(Store(self.path).read()["active"])
        self.mock_time.return_value = parse_local(self.payload["start"])
        state = Store(self.path).read()
        self.assertTrue(state["active"])
        self.assertEqual(state["text"], self.payload["text"])
        self.assertEqual(state["display_color"], "#66ff66")
        self.mock_time.return_value = parse_local(self.payload["end"]) - 1
        self.assertTrue(Store(self.path).read()["active"])
        self.mock_time.return_value += 1
        self.assertFalse(Store(self.path).read()["active"])

    def test_edit_cancel_and_overlap(self):
        state = self.store.schedule(self.payload)
        ident = state["schedules"][0]["id"]
        with self.assertRaises(ValueError):
            self.store.schedule({**self.payload, "start": "2026-09-18T14:00"})
        changed = self.store.schedule({**self.payload, "id": ident, "text": "Updated"})
        self.assertEqual(changed["schedules"][0]["text"], "Updated")
        self.store.schedule({**self.payload, "start": "2026-09-18T15:00", "end": "2026-09-18T16:00"})
        self.store.cancel({"id": ident})
        self.assertEqual(len(Store(self.path).read()["schedules"]), 1)

    def test_clear_active_preserves_future_and_no_resurrection(self):
        self.store.save("Now", minutes=1440)
        self.store.schedule(self.payload)
        self.store.schedule({**self.payload, "start": "2026-09-18T16:00", "end": "2026-09-18T17:00"})
        self.assertEqual(self.store.read()["text"], "Now")
        self.mock_time.return_value = parse_local("2026-09-18T13:00")
        with self.assertRaises(ValueError):
            self.store.save("Interrupt")
        self.store.save("")
        self.assertFalse(self.store.read()["active"])
        self.assertEqual(len(self.store.read()["schedules"]), 1)
        self.mock_time.return_value = parse_local("2026-09-18T16:00")
        self.assertTrue(self.store.read()["active"])

    def test_edit_active_and_stale_edit_rejected(self):
        ident = self.store.schedule(self.payload)["schedules"][0]["id"]
        self.mock_time.return_value = parse_local("2026-09-18T13:00")
        self.store.schedule({**self.payload, "id": ident, "text": "Changed"})
        self.assertEqual(self.store.read()["text"], "Changed")
        self.store.cancel({"id": ident})
        with self.assertRaises(ValueError):
            self.store.schedule({**self.payload, "id": ident})

    def test_time_validation_and_dst(self):
        self.assertEqual(parse_local("2026-07-01T12:00") % 86400, 16*3600)
        self.assertEqual(parse_local("2026-01-01T12:00") % 86400, 17*3600)
        for value in ["2026-03-08T02:30", "2026-11-01T01:30", "", "2026-02-30T12:00", None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_local(value)
        for fields in [{"end": self.payload["start"]}, {"start": "2026-09-18T09:00"}, {"end": "2026-09-17T15:00"}]:
            with self.assertRaises(ValueError):
                self.store.schedule({**self.payload, **fields})

    def test_failed_save_keeps_schedule_and_legacy_file(self):
        self.store.save("Old")
        before = self.path.read_text()
        with patch("server.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.schedule(self.payload)
        self.assertEqual(self.path.read_text(), before)
        self.assertEqual(self.store.read()["schedules"], [])
