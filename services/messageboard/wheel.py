"""Pixel wheel rendering and recoverable, temporary Tronbyt takeover."""
import base64
import io
import json
import math
import os
import secrets
import tempfile
import threading
import time
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw

COLORS = ['#ff6688', '#55ccff', '#ffcc55', '#88dd66', '#bb88ff', '#ff9955', '#55ddbb', '#ee88dd', '#aaccff', '#dddd66', '#ffaaaa', '#88bbbb']
FONT = json.loads((Path(__file__).with_name('font.js')).read_text().split('const boardFont = ', 1)[1].strip().rstrip(';'))
INSTALLATION = 'messageboard-wheel'


def labels_from(payload):
    labels = payload.get('labels') if isinstance(payload, dict) else None
    if not isinstance(labels, list) or not 2 <= len(labels) <= 12:
        raise ValueError('Enter 2–12 labels, one per line.')
    result = []
    for label in labels:
        if not isinstance(label, str):
            raise ValueError('Each label must be text.')
        label = ' '.join(unicodedata.normalize('NFC', label).split())
        if not 1 <= len(label) <= 20 or any(c not in FONT for c in label):
            raise ValueError('Use 1–20 characters per label: letters, numbers and simple punctuation. Swedish letters work.')
        if label.casefold() in [s.casefold() for s in result]:
            raise ValueError('Use distinct labels so each choice has one equal chance.')
        result.append(label)
    return result


def width(text):
    return sum(FONT[c]['width'] for c in text)


def text(image, value, x, y, color='white'):
    for c in value:
        for dx, dy in FONT[c]['pixels']:
            if 0 <= x + dx < 64 and 0 <= y + dy < 32:
                image.putpixel((x + dx, y + dy), Image.new('RGB', (1, 1), color).getpixel((0, 0)))
        x += FONT[c]['width']


def wheel_frame(labels, angle, winner=None):
    image = Image.new('RGB', (64, 32))
    n = len(labels)
    for y in range(32):
        for x in range(30):
            dx, dy = x - 14, y - 16
            if dx * dx + dy * dy <= 13 * 13:
                a = (math.atan2(dy, dx) - angle) % math.tau
                index = int(a / math.tau * n) % n
                image.putpixel((x, y), Image.new('RGB', (1, 1), COLORS[index]).getpixel((0, 0)))
    d = ImageDraw.Draw(image)
    d.ellipse((12, 14, 16, 18), fill='white')
    d.polygon([(27, 14), (27, 18), (23, 16)], fill='white')
    selected = int(((-angle) % math.tau) / math.tau * n) % n
    text(image, 'PICK' if winner is None else 'WINS', 33, 2, '#ffdd66')
    label = labels[selected if winner is None else winner]
    # Two short lines alongside the wheel; the full winner follows on its own screen.
    lines, line = [], ''
    for c in label:
        if width(line + c) > 30:
            lines.append(line)
            line = ''
        line += c
    lines.append(line)
    for i, line in enumerate(lines[:2]):
        text(image, line, 33, 13 + 9 * i)
    return image


def render(labels, winner):
    # The fixed pointer is at angle zero. End at the selected segment's center.
    end = 6 * math.tau - (winner + .5) * math.tau / len(labels)
    frames = [wheel_frame(labels, end * (1 - (1 - i / 80) ** 3)) for i in range(81)]
    frames[-1] = wheel_frame(labels, end, winner)
    result = Image.new('RGB', (64, 32))
    text(result, 'WINNER', 17, 0, COLORS[winner])
    lines, line = [], ''
    for c in labels[winner]:
        if width(line + c) > 60:
            lines.append(line)
            line = ''
        line += c
    lines.append(line)
    for i, line in enumerate(lines):
        text(result, line, (64 - width(line)) // 2, 8 + i * 8)
    frames.append(result)
    output = io.BytesIO()
    frames[0].save(output, format='WEBP', save_all=True, append_images=frames[1:],
                   duration=[100] * 80 + [2000, 120000], lossless=True, loop=0, method=4)
    return output.getvalue()


class Tronbyt:
    def __init__(self):
        self.base = os.environ.get('WHEEL_TRONBYT_URL', '').rstrip('/')
        self.key = os.environ.get('WHEEL_TRONBYT_KEY', '')
        self.device = os.environ.get('WHEEL_TRONBYT_DEVICE', '')

    @property
    def configured(self):
        return bool(self.base and self.key and self.device)

    def call(self, method, suffix='', payload=None):
        if not self.configured:
            raise ValueError('The wheel needs a Tronbyt device connection. Configure it on the Pi first.')
        url = self.base + '/v0/devices/' + quote(self.device, safe='') + suffix
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(url, data=data, method=method, headers={
            'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        try:
            with urlopen(req, timeout=8) as response:
                body = response.read()
                try:
                    return json.loads(body)
                except ValueError:
                    return {}
        except (HTTPError, URLError, TimeoutError) as exc:
            raise ValueError('Could not reach the Tronbyt device API. Check the Pi connection and device key.') from exc


class Wheel:
    def __init__(self, path, api=None, worker=True):
        self.path = Path(path)
        self.api = api or Tronbyt()
        self.lock = threading.RLock()
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.error = ''
        self.stop = threading.Event()
        if worker:
            threading.Thread(target=self._worker, daemon=True).start()

    def _save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix='.wheel-')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(state, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
            self.state = state
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def read(self):
        with self.lock:
            state = self.state
            return {'configured': self.api.configured, 'active': bool(state.get('active')),
                    'id': state.get('id'), 'labels': state.get('labels', []),
                    'winner': state.get('winner') if time.time() >= state.get('result_at', 0) else None,
                    'result_at': state.get('result_at'), 'release_at': state.get('release_at'),
                    'error': self.error}

    def spin(self, payload):
        labels = labels_from(payload)
        with self.lock:
            if self.state.get('active'):
                raise ValueError('A round is already on the display. Tap Done before starting another.')
            if not self.api.configured:
                raise ValueError('Configure the Tronbyt device connection on the Pi before spinning.')
            winner = secrets.randbelow(len(labels))
            image = render(labels, winner)
            device = self.api.call('GET')
            round_id = secrets.token_hex(12)
            installation = INSTALLATION + '-' + round_id
            state = {'active': True, 'id': round_id, 'installation': installation, 'labels': labels, 'winner': winner,
                     'previous_pin': device.get('pinnedApp') or '', 'wheel_pin': None,
                     'result_at': time.time() + 10, 'release_at': time.time() + 68}
            # Persist recovery information before any remote mutation.
            self._save(state)
            try:
                install = '/installations/' + installation
                self.api.call('POST', '/push', {'installationID': installation,
                              'image': base64.b64encode(image).decode(), 'background': True})
                app = self.api.call('GET', install)
                state = dict(self.state, wheel_pin=app['id'])
                self._save(state)
                self.api.call('PATCH', install, {'pinned': True, 'displayTimeSec': 68,
                                                'showFullAnimation': 'false'})
                self.api.call('POST', '/push', {'installationID': installation,
                              'image': base64.b64encode(image).decode(), 'background': False})
                now = time.time()
                self._save(dict(self.state, result_at=now + 10, release_at=now + 68))
            except Exception:
                try:
                    self._release()
                except Exception:
                    self.error = 'Display cleanup is pending. The Pi will retry automatically.'
                raise
            self.error = ''
            return self.read()

    def _release(self):
        device = self.api.call('GET')
        # Don't undo a new pin chosen manually in Manager during this round.
        if device.get('pinnedApp') == self.state.get('wheel_pin') and self.state.get('wheel_pin'):
            self.api.call('PATCH', '', {'pinnedApp': self.state.get('previous_pin') or ''})
        try:
            self.api.call('DELETE', '/installations/' + self.state['installation'])
        except ValueError:
            # A timed-out delete may already have completed.
            apps = self.api.call('GET', '/installations')['installations']
            if any(a['id'] in (self.state['installation'], self.state.get('wheel_pin')) for a in apps):
                raise
        self._save(dict(self.state, active=False))
        self.error = ''

    def done(self, payload):
        with self.lock:
            if not isinstance(payload, dict) or payload.get('id') != self.state.get('id'):
                raise ValueError('This round has changed. Refresh the page.')
            if self.state.get('active'):
                self._release()
            return self.read()

    def _worker(self):
        while not self.stop.wait(2):
            with self.lock:
                if self.state.get('active') and time.time() >= self.state['release_at']:
                    try:
                        self._release()
                    except Exception:
                        self.error = 'Could not restore rotation yet. Retrying automatically; Done can also retry.'
