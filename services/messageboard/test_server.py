import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from server import Server, Store, validate


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "message.json"
        self.store = Store(self.path)
        self.server = Server(("127.0.0.1", 0), self.store, ["127.0.0.1"])
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, method, path, payload=None, headers=None, raw=None):
        body = raw if raw is not None else json.dumps(payload) if payload is not None else None
        common = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.port}"}
        common.update(headers or {})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        conn.request(method, path, body=body, headers=common)
        response = conn.getresponse()
        data = response.read()
        status = response.status
        conn.close()
        return status, data

    def test_send_fetch_restart_and_clear(self):
        code, body = self.request("POST", "/api/message", {"text": "Välkommen till Malmö!", "color": "green", "expires_minutes": 60})
        self.assertEqual(code, 200)
        state = json.loads(body)
        self.assertTrue(state["active"])
        self.assertEqual(state["display_color"], "#66ff66")
        self.assertEqual(Store(self.path).read()["text"], state["text"])
        self.assertEqual(json.loads(self.request("GET", "/api/message")[1])["text"], state["text"])
        self.assertEqual(self.request("POST", "/api/clear", {})[0], 200)
        self.assertFalse(Store(self.path).read()["active"])

    def test_expiry(self):
        with patch("server.time.time", return_value=1000):
            self.store.save("A surprise", minutes=15)
        with patch("server.time.time", return_value=1900):
            state = self.store.read()
            self.assertFalse(state["active"])
            self.assertTrue(state["expired"])
            self.assertEqual(state["text"], "")

    def test_one_hour_rotation_window_and_replacement(self):
        with patch("server.time.time", return_value=1000):
            code, body = self.request("POST", "/api/message", {"text": "First"})
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(body)["expires_at"], 4600)
        with patch("server.time.time", return_value=4599):
            self.assertTrue(Store(self.path).read()["active"])
        with patch("server.time.time", return_value=4600):
            self.assertFalse(Store(self.path).read()["active"])
            self.request("POST", "/api/message", {"text": "Second"})
            self.assertEqual(self.store.read()["expires_at"], 8200)
        with patch("server.time.time", return_value=8200):
            self.assertFalse(self.store.read()["active"])

    def test_all_time_limits_survive_restart_and_expire(self):
        for minutes in [5, 15, 30, 60, 180, 360, 1440]:
            with self.subTest(minutes=minutes):
                with patch("server.time.time", return_value=1000):
                    code, body = self.request("POST", "/api/message", {"text": "Timed", "expires_minutes": minutes})
                    self.assertEqual(code, 200)
                    deadline = 1000 + minutes * 60
                    self.assertEqual(json.loads(body)["expires_at"], deadline)
                with patch("server.time.time", return_value=deadline - 1):
                    self.assertTrue(Store(self.path).read()["active"])
                with patch("server.time.time", return_value=deadline):
                    self.assertFalse(Store(self.path).read()["active"])
        for minutes in [0, 240, -1, 60.0, "60", None]:
            self.assertEqual(self.request("POST", "/api/message", {"text": "Invalid", "expires_minutes": minutes})[0], 400)

    def test_flowers_are_independent_and_persist(self):
        self.store.save("Board")
        code, body = self.request("POST", "/api/flowers", {"text": "Anna, Malmö!", "expires_minutes": 5})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["text"], "Anna, Malmö!")
        self.assertEqual(self.store.read()["text"], "Board")
        self.assertEqual(Store(self.path.with_name("flowers.json")).read()["text"], "Anna, Malmö!")
        self.assertEqual(self.request("GET", "/flowers")[0], 200)
        self.assertEqual(self.request("GET", "/flowers.js")[0], 200)
        self.assertEqual(json.loads(self.request("GET", "/api/flowers")[1])["text"], "Anna, Malmö!")
        self.assertEqual(self.request("POST", "/api/flowers/clear", {})[0], 200)
        self.assertFalse(self.server.flowers.read()["active"])
        self.assertEqual(self.store.read()["text"], "Board")

    def test_schedule_api_for_both_composers(self):
        from scheduling import parse_local
        with patch("server.time.time", return_value=parse_local("2026-09-18T10:00")):
            for endpoint in ["/api/message", "/api/flowers"]:
                payload = {"text": "Scheduled Malmö", "start": "2026-09-18T12:00", "end": "2026-09-18T15:00"}
                code, body = self.request("POST", endpoint + "/schedule", payload)
                self.assertEqual(code, 200)
                state = json.loads(body)
                self.assertFalse(state["active"])
                ident = state["schedules"][0]["id"]
                self.assertEqual(self.request("POST", endpoint + "/schedule", {**payload, "id": ident, "text": "Edited"})[0], 200)
                self.assertEqual(self.request("POST", endpoint + "/schedule", payload)[0], 400)
                self.assertEqual(self.request("POST", endpoint + "/cancel", {"id": ident})[0], 200)
                self.assertEqual(json.loads(self.request("GET", endpoint)[1])["schedules"], [])

    def test_gif_endpoints_and_request_protection(self):
        from test_gifstore import upload_data
        self.assertEqual(self.request("GET", "/gifs")[0], 200)
        self.assertEqual(self.request("POST", "/api/gifs/upload", upload_data(), {"Origin": "http://evil.example"})[0], 403)
        code, body = self.request("POST", "/api/gifs/upload", upload_data())
        self.assertEqual(code, 200)
        ident = json.loads(body)["items"][0]["id"]
        self.assertEqual(self.request("GET", "/api/gifs/preview/" + ident)[0], 200)
        playback = json.loads(self.request("GET", "/api/gifs/next")[1])
        self.assertEqual(sum(playback["holds"]) * playback["delay"], 10000)
        self.assertEqual(self.request("POST", "/api/gifs/change", {"action": "remove", "id": ident})[0], 200)
        self.assertEqual(self.request("GET", "/api/gifs/preview/" + ident)[0], 404)
        self.assertEqual(json.loads(self.request("GET", "/api/gifs/next")[1])["frames"], [])

    def test_smart_punctuation_and_composed_unicode(self):
        text, _, _ = validate({"text": "  There’s a gift…  Malmo\u0308 "})
        self.assertEqual(text, "There's a gift... Malmö")

    def test_bad_messages_do_not_replace_good_message(self):
        self.store.save("Keep this")
        for payload in [{"text": ""}, {"text": "x"*121}, {"text": "Hi 🥳"}, {"text": "ok", "color": []}, {"text": "ok", "expires_minutes": True}, []]:
            self.assertEqual(self.request("POST", "/api/message", payload)[0], 400)
            self.assertEqual(self.store.read()["text"], "Keep this")

    def test_foreign_origin_and_host_blocked(self):
        self.assertEqual(self.request("POST", "/api/message", {"text": "bad"}, {"Origin": "http://example.com"})[0], 403)
        self.assertEqual(self.request("GET", "/api/message", headers={"Host": "example.com"})[0], 403)

    def test_form_body_and_invalid_json(self):
        self.assertEqual(self.request("POST", "/api/message", raw="text=bad", headers={"Content-Type": "application/x-www-form-urlencoded"})[0], 415)
        self.assertEqual(self.request("POST", "/api/message", raw="{")[0], 400)
        self.assertEqual(self.request("POST", "/api/message", raw="x"*5000)[0], 413)

    def test_atomic_save_failure_preserves_old_state(self):
        self.store.save("Original")
        with patch("server.os.replace", side_effect=OSError("disk unavailable")):
            self.assertEqual(self.request("POST", "/api/message", {"text": "New"})[0], 500)
        self.assertEqual(self.store.read()["text"], "Original")
        self.assertEqual(Store(self.path).read()["text"], "Original")

    def test_only_known_static_files_are_served(self):
        self.assertEqual(self.request("GET", "/")[0], 200)
        self.assertEqual(self.request("GET", "/app.js")[0], 200)
        self.assertEqual(self.request("GET", "/../server.py")[0], 404)
        self.assertEqual(self.request("GET", "/data/message.json")[0], 404)


if __name__ == "__main__":
    unittest.main()
