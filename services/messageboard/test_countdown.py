import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from countdown import Timer, duration, parse, preview, render_clip, frame, clock
from test_wheel import FakeAPI
import test_server


class TimerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.api = FakeAPI(pin=None)
        self.path = Path(self.tmp.name) / 'timer.json'
        self.timer = Timer(self.path, self.api, worker=False)

    def tearDown(self):
        self.tmp.cleanup()

    def start(self, seconds=60):
        with patch('countdown.render_clip', return_value=b'webp'), patch('countdown.time.time', return_value=1000):
            return self.timer.start({'text': 'Pizza party!', 'duration': f'{seconds}s'})

    def test_free_text_duration_and_bounds(self):
        for value, expected in [('45 min', 2700), ('1h 30m', 5400), ('00:45:00', 2700), ('59:59', 3599), ('1 hour 2 minutes 3 seconds', 3723), ('24h', 86400)]:
            self.assertEqual(duration(value), expected)
        for value in ['', '45', '-1h', '1.5h', '00:60:00', '1h rubbish', '0s', '25h', None]:
            with self.assertRaises(ValueError):
                duration(value)
        self.assertEqual(clock(3599), '59:59')
        self.assertEqual(clock(3598), '59:58')
        self.assertEqual(clock(3600), '01:00:00')

    def test_preview_matches_renderer_and_rejects_overflow(self):
        payload = {'text': 'Pizza party!', 'duration': '59:59'}
        value, lines, _ = parse(payload)
        data = preview(payload)
        image = Image.open(io.BytesIO(base64.b64decode(data['image']))).convert('RGB')
        self.assertEqual(image.tobytes(), frame(lines, 3599).tobytes())
        self.assertEqual(data['text'], value)
        self.assertEqual(image.size, (64, 32))
        parse({'text': 'Hej Malmö!', 'duration': '1m'})
        for message in ['This message is much too long to fit in two short lines on the screen', '😀', '']:
            with self.assertRaises(ValueError):
                parse({'text': message, 'duration': '1m'})

    def test_animation_seconds_and_zero_transition(self):
        lines = ['Pizza!']
        with Image.open(io.BytesIO(render_clip(lines, 1002, 1000))) as image:
            self.assertEqual(image.size, (64, 32))
            image.seek(0); image.load()
            self.assertEqual(image.info['duration'], 1000)
            self.assertEqual(image.convert('RGB').tobytes(), frame(lines, 2).tobytes())
            image.seek(1); image.load()
            self.assertEqual(image.info['timestamp'], 1000)
            self.assertEqual(image.convert('RGB').tobytes(), frame(lines, 1).tobytes())
            image.seek(2); image.load()
            self.assertEqual(image.info['timestamp'], 2000)
            self.assertEqual(image.convert('RGB').tobytes(), frame(lines, 0, 0).tobytes())
            total = 0
            for i in range(image.n_frames):
                image.seek(i);image.load();total += image.info['duration']
            self.assertEqual(total, 40000)

    def test_countdown_fireworks_release_and_persistence(self):
        state = self.start()
        self.assertEqual(state['ends_at'], 1060)
        self.assertEqual(state['release_at'], 1120)
        self.assertEqual(self.api.pin, 'internal-wheel')
        timer = Timer(self.path, self.api, worker=False)
        with patch('countdown.time.time', return_value=1060), patch('countdown.render_clip', return_value=b'webp'):
            timer.tick()
            self.assertEqual(timer.read()['phase'], 'finishing')
            self.assertTrue(timer.read()['active'])
        with patch('countdown.time.time', return_value=1120):
            timer.tick()
        self.assertFalse(timer.read()['active'])
        self.assertFalse(self.api.pin)
        self.assertFalse(self.api.exists)

    def test_long_timer_refresh_uses_saved_deadline(self):
        state = self.start(7200)
        with patch('countdown.time.time', return_value=1030), patch('countdown.render_clip', return_value=b'webp') as render:
            self.timer.tick()
            render.assert_called_once_with(self.timer.state['lines'], state['ends_at'], 1030)
            self.assertEqual(self.timer.read()['remaining'], 7170)

    def test_cancel_retry_and_stale_request(self):
        state = self.start()
        with self.assertRaises(ValueError):
            self.timer.cancel({'id': 'old'})
        original = self.api.call
        def unavailable(*args, **kwargs):
            raise ValueError('offline')
        self.api.call = unavailable
        with self.assertRaises(ValueError):
            self.timer.cancel({'id': state['id']})
        self.assertTrue(self.timer.state['cancel_pending'])
        self.api.call = original
        self.timer.tick()
        self.assertFalse(self.timer.read()['active'])
        self.assertFalse(self.api.pin)

    def test_completion_returns_to_rotation_even_if_previously_pinned(self):
        self.api.pin = "weather"
        self.start()
        with patch("countdown.time.time", return_value=1120):
            self.timer.tick()
        self.assertFalse(self.api.pin)

    def test_manual_pin_is_preserved(self):
        self.start()
        self.api.pin = 'weather'
        self.timer.next_push = 0
        self.timer.tick()
        self.assertFalse(self.timer.read()['active'])
        self.assertEqual(self.api.pin, 'weather')

    def test_restart_after_expiry_cleans_up(self):
        self.start()
        restarted = Timer(self.path, self.api, worker=False)
        with patch('countdown.time.time', return_value=1200):
            restarted.tick()
        self.assertFalse(restarted.read()['active'])

    def test_setup_failure_cleans_up(self):
        self.api.fail_pin = True
        with self.assertRaises(ValueError):
            self.start()
        self.assertFalse(self.timer.read()['active'])
        self.assertFalse(self.api.exists)

    def test_no_overlapping_timer(self):
        self.start()
        with self.assertRaises(ValueError):
            self.start()


class TimerHTTPTests(unittest.TestCase):
    setUp = test_server.BoardTests.setUp
    tearDown = test_server.BoardTests.tearDown
    request = test_server.BoardTests.request

    def test_preview_routes_and_request_protection(self):
        payload = {'text': 'Pizza party!', 'duration': '1h'}
        self.assertEqual(self.request('GET', '/timer')[0], 200)
        self.assertEqual(self.request('GET', '/timer.js')[0], 200)
        self.assertEqual(self.request('GET', '/api/timer')[0], 200)
        code, body = self.request('POST', '/api/timer/preview', payload)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['seconds'], 3600)
        self.assertEqual(self.request('POST', '/api/timer/preview', payload, {'Origin':'http://other.example'})[0], 403)
        self.assertEqual(self.request('POST', '/api/timer/preview', {'text': 'Hi', 'duration': 'bad'})[0], 400)

    def test_wheel_and_timer_mutual_exclusion(self):
        self.server.timer.stop.set()
        self.server.wheel.stop.set()
        self.server.timer.api = FakeAPI(pin=None)
        self.server.wheel.state = {'active': True}
        payload = {'text': 'Pizza!', 'duration': '1m'}
        self.assertEqual(self.request('POST', '/api/timer/start', payload)[0], 400)
        self.server.wheel.state = {}
        with patch('countdown.render_clip', return_value=b'webp'):
            code, body = self.request('POST', '/api/timer/start', payload)
        self.assertEqual(code, 200)
        state = json.loads(body)
        self.assertEqual(self.request('POST', '/api/wheel/spin', {'labels':['A','B']})[0], 400)
        self.assertEqual(self.request('POST', '/api/timer/cancel', {'id':state['id']})[0], 200)


if __name__ == '__main__':
    unittest.main()
