import io
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from wheel import Wheel, labels_from, render


class FakeAPI:
    configured = True

    def __init__(self, pin='weather'):
        self.pin = pin
        self.exists = False
        self.fail_pin = False
        self.calls = []

    def call(self, method, suffix='', payload=None):
        self.calls.append((method, suffix, payload))
        if method == 'GET' and not suffix:
            return {'pinnedApp': self.pin}
        if method == 'GET' and suffix == '/installations':
            return {'installations': [{'id': 'internal-wheel'}] if self.exists else []}
        if method == 'GET':
            return {'id': 'internal-wheel'}
        if method == 'POST':
            self.exists = True
        if method == 'PATCH':
            if suffix:
                if self.fail_pin:
                    raise ValueError('Pin failed')
                self.pin = 'internal-wheel'
            else:
                self.pin = payload['pinnedApp'] or None
        if method == 'DELETE':
            self.exists = False
        return {}


class WheelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'wheel.json'
        self.api = FakeAPI()
        self.wheel = Wheel(self.path, self.api, worker=False)

    def tearDown(self):
        self.tmp.cleanup()

    def spin(self):
        with patch('wheel.render', return_value=b'webp'), patch('wheel.secrets.randbelow', return_value=1):
            return self.wheel.spin({'labels': ['Pizza', 'Tacos']})

    def test_labels(self):
        self.assertEqual(labels_from({'labels': ['  Åsa ', 'Östen']}), ['Åsa', 'Östen'])
        for labels in [['A'], ['A', 'a'], ['A', '😀'], ['A', 'x' * 21], [1, 'A']]:
            with self.assertRaises(ValueError):
                labels_from({'labels': labels})

    def test_takeover_hides_result_and_restores_previous_pin(self):
        state = self.spin()
        self.assertTrue(state['active'])
        self.assertIsNone(state['winner'])
        self.assertEqual(self.api.pin, 'internal-wheel')
        with self.assertRaises(ValueError):
            self.spin()
        with self.assertRaises(ValueError):
            self.wheel.done({'id': 'old-round'})
        result = self.wheel.done({'id': state['id']})
        self.assertFalse(result['active'])
        self.assertEqual(self.api.pin, 'weather')
        self.assertFalse(self.api.exists)

    def test_restart_restores_persisted_pin_and_result(self):
        state = self.spin()
        restarted = Wheel(self.path, self.api, worker=False)
        restarted.state['result_at'] = time.time() - 1
        self.assertEqual(restarted.read()['winner'], 1)
        restarted.done({'id': state['id']})
        self.assertEqual(self.api.pin, 'weather')

    def test_manual_pin_change_is_preserved(self):
        state = self.spin()
        self.api.pin = 'clock'
        self.wheel.done({'id': state['id']})
        self.assertEqual(self.api.pin, 'clock')

    def test_pin_failure_cleans_up_created_image(self):
        self.api.fail_pin = True
        with self.assertRaises(ValueError):
            self.spin()
        self.assertFalse(self.api.exists)
        self.assertFalse(self.wheel.read()['active'])
        self.assertEqual(self.api.pin, 'weather')

    def test_cleanup_failure_keeps_recovery_record(self):
        state = self.spin()
        original = self.api.call
        def fail(method, suffix='', payload=None):
            if method == 'PATCH' and not suffix:
                raise ValueError('offline')
            return original(method, suffix, payload)
        self.api.call = fail
        with self.assertRaises(ValueError):
            self.wheel.done({'id': state['id']})
        self.assertTrue(self.wheel.read()['active'])
        self.api.call = original
        self.wheel.done({'id': state['id']})
        self.assertFalse(self.wheel.read()['active'])

    def test_render_is_64_by_32_and_lands_on_selected_color(self):
        for winner in range(3):
            with Image.open(io.BytesIO(render(['Pizza', 'Tacos', 'Sushi'], winner))) as image:
                self.assertEqual(image.size, (64, 32))
                self.assertGreater(image.n_frames, 70)
                image.seek(image.n_frames - 2)
                from PIL import ImageColor
                from wheel import COLORS
                self.assertEqual(image.convert('RGB').getpixel((24, 20)), ImageColor.getrgb(COLORS[winner]))
                image.seek(image.n_frames - 1)
                image.load()
                self.assertEqual(image.info['timestamp'], 10000)
                self.assertEqual(image.info['duration'], 120000)


if __name__ == '__main__':
    unittest.main()
