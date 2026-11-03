"""Persistent countdown, shared pixel preview, and temporary device takeover."""
import base64
import io
import math
import re
import secrets
import time
import unicodedata
from PIL import Image, ImageDraw
from wheel import FONT, Wheel, text, width

MAX_SECONDS = 24 * 3600


def duration(value):
    if not isinstance(value, str):
        raise ValueError('Enter a duration such as 45 min, 1h 30m, or 00:45:00.')
    value = value.strip().lower()
    if re.fullmatch(r'\d{1,2}:\d{2}(?::\d{2})?', value):
        parts = [int(p) for p in value.split(':')]
        if any(p >= 60 for p in parts[1:]):
            raise ValueError('Minutes and seconds after a colon must be below 60.')
        seconds = parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        pattern = r'(\d+)\s*(hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)'
        matches = list(re.finditer(pattern, value))
        if not matches or re.sub(pattern, '', value).strip():
            raise ValueError('Use units (45 min, 1h 30m) or MM:SS / HH:MM:SS.')
        seconds = sum(int(m[1]) * (3600 if m[2].startswith('h') else 60 if m[2].startswith('m') else 1) for m in matches)
    if not 1 <= seconds <= MAX_SECONDS:
        raise ValueError('Choose a duration between 1 second and 24 hours.')
    return seconds


def message_lines(value):
    if not isinstance(value, str):
        raise ValueError('Enter a message.')
    value = ' '.join(unicodedata.normalize('NFC', value).translate(str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"', '–': '-', '—': '-', '…': '...'})).split())
    if not 1 <= len(value) <= 120 or any(c not in FONT for c in value):
        raise ValueError('Use letters, numbers and simple punctuation; Swedish letters work. No emoji.')
    lines, line = [], ''
    for word in value.split():
        candidate = line + (' ' if line else '') + word
        if width(candidate) <= 60:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = ''
            for char in word:
                if width(line + char) > 60:
                    lines.append(line)
                    line = ''
                line += char
    if line:
        lines.append(line)
    if len(lines) > 2:
        raise ValueError('This message needs more than two lines. Shorten it so the countdown stays visible.')
    return value, lines


def parse(payload):
    if not isinstance(payload, dict):
        raise ValueError('Enter a message and duration.')
    value, lines = message_lines(payload.get('text'))
    return value, lines, duration(payload.get('duration'))


def clock(seconds):
    seconds = max(0, int(seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'


def frame(lines, remaining, celebration=0):
    image = Image.new('RGB', (64, 32))
    for i, line in enumerate(lines):
        text(image, line, (64 - width(line)) // 2, i * 8 + (4 if len(lines) == 1 else 0))
    if remaining > 0:
        label = clock(remaining)
        scale = 2 if width(label) * 2 <= 60 else 1
        digits = Image.new('RGB', (64, 32))
        text(digits, label, 0, 0, '#ffdd66')
        crop = digits.crop((0, 0, width(label), 8))
        crop = crop.resize((crop.width * scale, 8 * scale), Image.Resampling.NEAREST)
        image.paste(crop, ((64 - crop.width) // 2, 16 + (16 - crop.height) // 2))
    else:
        d = ImageDraw.Draw(image)
        colors = ['#ffdd55', '#ff77bb', '#66ddff']
        for i, cx in enumerate([12, 32, 52]):
            age = (celebration + i * 3) % 12
            radius = 1 + age // 2
            for spoke in range(8):
                angle = spoke * math.tau / 8
                x, y = round(cx + math.cos(angle) * radius), round(24 + math.sin(angle) * radius)
                if y >= 17 and (age < 9 or spoke % 2 == age % 2):
                    d.point((x, y), fill=colors[i])
        text(image, '00:00', (64 - width('00:00')) // 2, 21)
    return image


def encoded(image, kind='PNG'):
    output = io.BytesIO()
    image.save(output, format=kind)
    return base64.b64encode(output.getvalue()).decode()


def preview(payload):
    value, lines, seconds = parse(payload)
    return {'text': value, 'lines': lines, 'seconds': seconds, 'clock': clock(seconds),
            'image': encoded(frame(lines, seconds)), 'finish_image': encoded(frame(lines, 0, 4))}


def render_clip(lines, ends_at, now):
    # Forty seconds of wall-clock-derived frames, refreshed every 25 seconds.
    # Countdown frames merge losslessly into one-second holds in the WebP.
    frames = [frame(lines, math.ceil(ends_at - now - i / 4), int((now + i / 4 - ends_at) * 4)) for i in range(160)]
    output = io.BytesIO()
    frames[0].save(output, format='WEBP', save_all=True, append_images=frames[1:],
                   duration=250, lossless=True, loop=0, method=0)
    return output.getvalue()


class Timer(Wheel):
    """Reuse the wheel's atomic state storage and recoverable pin cleanup."""
    def __init__(self, path, api=None, worker=True):
        self.next_push = 0
        super().__init__(path, api=api, worker=worker)

    def read(self):
        with self.lock:
            now = time.time()
            state = self.state
            active = bool(state.get('active'))
            return {'configured': self.api.configured, 'active': active, 'id': state.get('id'),
                    'text': state.get('text', ''), 'ends_at': state.get('ends_at'),
                    'release_at': state.get('release_at'), 'server_now': now,
                    'remaining': max(0, math.ceil(state.get('ends_at', 0) - now)) if active else 0,
                    'phase': ('finishing' if now >= state.get('ends_at', 0) else 'countdown') if active else 'idle',
                    'error': self.error,
                    'image': encoded(frame(state['lines'], max(0, math.ceil(state['ends_at'] - now)), int((now - state['ends_at']) * 4))) if active else None}

    def start(self, payload):
        value, lines, seconds = parse(payload)
        with self.lock:
            if self.state.get('active'):
                raise ValueError('A timer is already active. Cancel it before starting another.')
            if not self.api.configured:
                raise ValueError('Configure the Tronbyt device connection on the Pi first (same settings as Spin the Wheel).')
            device = self.api.call('GET')
            token = secrets.token_hex(12)
            now = time.time()
            self._save({'active': True, 'id': token, 'installation': 'messageboard-timer-' + token,
                        'text': value, 'lines': lines, 'ends_at': now + seconds,
                        'release_at': now + seconds + 60, 'previous_pin': '',
                        'wheel_pin': None, 'cancel_pending': False})
            try:
                self._push(background=True)
                install = '/installations/' + self.state['installation']
                app = self.api.call('GET', install)
                self._save(dict(self.state, wheel_pin=app['id']))
                self.api.call('PATCH', install, {'pinned': True, 'displayTimeSec': 40, 'showFullAnimation': 'false'})
                # Start the requested interval after installation setup.
                now = time.time()
                self._save(dict(self.state, ends_at=now + seconds, release_at=now + seconds + 60))
                self._push()
            except Exception:
                self._save(dict(self.state, cancel_pending=True, previous_pin=device.get('pinnedApp') or ''))
                try:
                    self._release()
                except Exception:
                    self.error = 'Timer setup failed; cleanup is pending and will retry automatically.'
                raise
            self.error = ''
            return self.read()

    def _push(self, background=False):
        now = time.time()
        image = render_clip(self.state['lines'], self.state['ends_at'], now)
        self.api.call('POST', '/push', {'installationID': self.state['installation'],
                      'image': base64.b64encode(image).decode(), 'background': background})
        self.next_push = now + 25

    def cancel(self, payload):
        with self.lock:
            if not isinstance(payload, dict) or payload.get('id') != self.state.get('id'):
                raise ValueError('This timer has changed. Refresh the page.')
            if self.state.get('active'):
                self._save(dict(self.state, cancel_pending=True))
                try:
                    self._release()
                except Exception:
                    self.error = 'Could not restore rotation yet. The Pi will keep retrying.'
                    raise
            return self.read()

    def tick(self):
        with self.lock:
            if not self.state.get('active'):
                return
            now = time.time()
            if self.state.get('cancel_pending') or now >= self.state['release_at']:
                self._release()
            elif now >= self.next_push:
                device = self.api.call('GET')
                if device.get('pinnedApp') != self.state.get('wheel_pin'):
                    # Respect manual unpinning, another app's takeover or a new pin.
                    self._release()
                    return
                self._push()
                self.error = ''

    def _worker(self):
        while not self.stop.wait(.5):
            try:
                self.tick()
            except Exception:
                with self.lock:
                    self.error = 'Display connection interrupted. The timer keeps running; the Pi will retry.'
                    self.next_push = time.time() + 5
                self.stop.wait(4.5)
