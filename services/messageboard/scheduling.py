"""One-off message windows in America/New_York, stored as UTC timestamps."""
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid

ZONE = ZoneInfo("America/New_York")


def parse_local(value):
    if not isinstance(value, str):
        raise ValueError("Choose a start and end date/time.")
    try:
        local = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise ValueError("Use a valid date and time.") from None
    candidates = set()
    for fold in (0, 1):
        aware = local.replace(tzinfo=ZONE, fold=fold)
        stamp = int(aware.timestamp())
        if datetime.fromtimestamp(stamp, ZONE).replace(tzinfo=None) == local:
            candidates.add(stamp)
    if len(candidates) != 1:
        raise ValueError("That time is skipped or repeated by daylight saving. Choose an unambiguous New York time.")
    return candidates.pop()


def save_schedule(existing, payload, text, color, now):
    ident = payload.get("id")
    if ident is not None and not isinstance(ident, str):
        raise ValueError("Invalid schedule ID.")
    current = next((item for item in existing if item["id"] == ident), None)
    if ident is not None and current is None:
        raise ValueError("This schedule no longer exists. Refresh the page.")
    start, end = parse_local(payload.get("start")), parse_local(payload.get("end"))
    if start >= end or end <= now:
        raise ValueError("End time must be after the start and in the future.")
    # An already-active window may keep its original start when edited.
    if start < now and not (current and start == current["starts_at"] and current["expires_at"] > now):
        raise ValueError("Start time must be in the future.")
    others = [item for item in existing if item["expires_at"] > now and item["id"] != ident]
    if any(start < item["expires_at"] and end > item["starts_at"] for item in others):
        raise ValueError("This overlaps another message for this app. Choose a different time.")
    if len(others) >= 100:
        raise ValueError("You can keep up to 100 upcoming messages per app.")
    item = {"id": ident or uuid.uuid4().hex, "text": text, "color": color,
            "starts_at": start, "expires_at": end, "updated_at": now}
    return sorted(others + [item], key=lambda item: item["starts_at"])
