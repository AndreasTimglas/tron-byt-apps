"""Bounded GIF uploads, display-sized frames and a persistent ordered playlist."""
import base64
import io
import json
import math
import os
import threading
import uuid
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD = 8 * 1024 * 1024


class GifStore:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.path = self.folder / "playlist.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {"items": [], "cursor": 0, "seconds": 10}

    def commit(self, state):
        temp = self.folder / (uuid.uuid4().hex + ".tmp")
        try:
            with temp.open("w") as f:
                json.dump(state, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, self.path)
            self.state = state
        finally:
            temp.unlink(missing_ok=True)

    def listing(self):
        with self.lock:
            return {"items": self.state["items"], "seconds": self.state["seconds"]}

    def upload(self, payload):
        if payload.get("fit") not in ("fit", "crop"):
            raise ValueError("Choose Fit or Crop.")
        encoded = payload.get("data")
        if not isinstance(encoded, str) or len(encoded) > MAX_UPLOAD * 4 // 3 + 4:
            raise ValueError("GIFs must be 8 MB or smaller.")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except ValueError:
            raise ValueError("Invalid upload encoding.") from None
        if not raw or len(raw) > MAX_UPLOAD:
            raise ValueError("GIFs must be 8 MB or smaller.")
        converted = self.convert(raw, payload["fit"])
        encoded_frames = converted["frames"]
        ident = uuid.uuid4().hex
        name = str(payload.get("name", "GIF")).replace("\\", "/").split("/")[-1][:100]
        with self.lock:
            if sum(p.stat().st_size for p in self.folder.iterdir() if p.is_file()) + len(raw) + len(json.dumps(encoded_frames)) > 512 * 1024 * 1024:
                raise ValueError("GIF storage is full (512 MB including removed files). Free space before uploading.")
            if len(self.state["items"]) >= 30:
                raise ValueError("The folder holds up to 30 GIFs. Remove one first.")
            # Immutable assets are written before publishing the playlist entry.
            (self.folder / (ident + ".gif")).write_bytes(raw)
            (self.folder / (ident + ".json")).write_text(json.dumps(converted))
            item = {"id": ident, "name": name, "fit": payload["fit"], "frames": len(encoded_frames)}
            self.commit({**self.state, "items": self.state["items"] + [item]})
        return self.listing()

    def convert(self, raw, fit):
        frames, durations = [], []
        try:
            with Image.open(io.BytesIO(raw)) as source:
                if source.format != "GIF":
                    raise ValueError("Upload a GIF file.")
                if source.width * source.height > 1024 * 1024:
                    raise ValueError("GIF dimensions must be at most one megapixel.")
                for index in range(301):
                    try:
                        source.seek(index)
                    except EOFError:
                        break
                    if index == 300:
                        raise ValueError("Use a GIF with at most 300 frames.")
                    rgba = source.convert("RGBA")
                    opaque = Image.new("RGBA", rgba.size, "black")
                    opaque.alpha_composite(rgba)
                    rgb = opaque.convert("RGB")
                    if fit == "crop":
                        frame = ImageOps.fit(rgb, (64, 32), method=Image.Resampling.LANCZOS)
                    else:
                        small = ImageOps.contain(rgb, (64, 32), method=Image.Resampling.LANCZOS)
                        frame = Image.new("RGB", (64, 32))
                        frame.paste(small, ((64-small.width)//2, (32-small.height)//2))
                    frames.append(frame.quantize(colors=256).convert("RGB"))
                    delay = int(source.info.get("duration", 100))
                    # Browsers conventionally hold unspecified/0/10 ms frames for 100 ms.
                    durations.append(100 if delay < 20 else delay)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValueError("This GIF could not be decoded safely.") from None
        if sum(durations) > 30000:
            raise ValueError("Use a GIF whose complete loop is 30 seconds or shorter.")
        encoded_frames = []
        for frame in frames:
            out = io.BytesIO()
            frame.save(out, format="PNG")
            encoded_frames.append(base64.b64encode(out.getvalue()).decode())
        return {"frames": encoded_frames, "durations": durations}

    def change(self, payload):
        with self.lock:
            items = list(self.state["items"])
            action = payload.get("action")
            if action == "duration":
                seconds = payload.get("seconds")
                if type(seconds) is not int or seconds not in (5, 10, 15):
                    raise ValueError("Choose 5, 10 or 15 seconds.")
                self.commit({**self.state, "seconds": seconds})
                return self.listing()
            index = next((i for i, item in enumerate(items) if item["id"] == payload.get("id")), None)
            if index is None:
                raise ValueError("GIF no longer exists. Refresh the page.")
            if action == "remove":
                items.pop(index)
            elif action in ("up", "down"):
                other = index + (-1 if action == "up" else 1)
                if 0 <= other < len(items):
                    items[index], items[other] = items[other], items[index]
            else:
                raise ValueError("Unknown action.")
            # Reset cursor after editing for a predictable first item.
            self.commit({**self.state, "items": items, "cursor": 0})
            # Retain removed assets in the volume as recoverable files.
        return self.listing()

    def playback(self, ident):
        item = next((item for item in self.state["items"] if item["id"] == ident), None)
        if item is None:
            raise ValueError("GIF not found.")
        path = self.folder / (ident + ".json")
        data = json.loads(path.read_text())
        if isinstance(data, list):
            # Rebuild older 10 fps conversions from the retained original GIF.
            data = self.convert((self.folder / (ident + ".gif")).read_bytes(), item["fit"])
            temp = path.with_suffix(".tmp")
            temp.write_text(json.dumps(data))
            os.replace(temp, path)
        remaining = self.state["seconds"] * 1000
        frames, durations = [], []
        index = 0
        while remaining:
            duration = min(data["durations"][index], remaining)
            frames.append(data["frames"][index])
            durations.append(duration)
            remaining -= duration
            index = (index + 1) % len(data["frames"])
        return frames, durations

    def frames(self, ident):
        return self.playback(ident)[0]

    def preview(self, ident):
        with self.lock:
            encoded, durations = self.playback(ident)
            frames = [Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB") for data in encoded]
        out = io.BytesIO()
        frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:], duration=durations, loop=0)
        return out.getvalue()

    def next(self):
        with self.lock:
            items = self.state["items"]
            if not items:
                return {"frames": [], "delay": 100, "holds": []}
            index = self.state["cursor"] % len(items)
            frames, durations = self.playback(items[index]["id"])
            delay = math.gcd(*durations)
            self.commit({**self.state, "cursor": (index+1) % len(items)})
            return {"frames": frames, "delay": delay, "holds": [duration // delay for duration in durations]}
