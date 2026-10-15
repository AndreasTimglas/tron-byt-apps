"""Run deterministic forecast checks and render every scene with Tronbyt Pixlet.
Usage: PIXLET=/path/to/pixlet python3 test_weatherplay.py
Requires Pillow for frame size and animation assertions.
"""
import os
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

CHECKS = """
def row(code, temp = 20, wind = 0, gust = 0, day = 1):
    return {"weather_code": code, "temperature_2m": temp, "wind_speed_10m": wind, "wind_gusts_10m": gust, "is_day": day}

def checks():
    for code, expected in [(0, "sun"), (3, "cloud"), (45, "fog"), (61, "rain"), (75, "snow"), (95, "storm")]:
        if choose([row(code)])["scene"] != expected:
            fail("Weather code selection")
    for rows, expected in [([row(61, 35)], "rain"), ([row(75), row(95)], "storm"), ([row(0, 30)], "fire"), ([row(0, 29)], "sun"), ([row(0, gust = 40)], "wind"), ([row(0, day = 0)], "night")]:
        if choose(rows)["scene"] != expected:
            fail("Scene precedence")
    hourly = {"time": [0, 3600, 7200, 10800, 14400]}
    for key in FIELDS:
        hourly[key] = [row(0)[key] for i in range(5)]
    hourly["weather_code"][0] = 95
    hourly["weather_code"][4] = 95
    data = {"hourly": hourly}
    if forecast(data, 1)["scene"] != "sun" or forecast(data, 0)["scene"] != "sun":
        fail("Forecast window includes past/outside hours")
    if forecast(data, 7201) != None or forecast({}, 0) != None:
        fail("Incomplete data")
    hourly["temperature_2m"][2] = None
    if forecast(data, 1) != None:
        fail("Null data")
    if coordinate("oops", 90) != None or coordinate("91", 90) != None:
        fail("Location validation")
    print("Forecast and scene checks passed")
"""

source = Path(__file__).with_name("weatherplay.star").read_text().split("def main(config):")[0]
with tempfile.TemporaryDirectory(prefix="weatherplay-") as directory:
    for scene in ["sun", "cloud", "night", "fog", "wind", "fire", "rain", "snow", "storm"]:
        fixture = Path(directory) / (scene + ".star")
        fixture.write_text(source + CHECKS + '\ndef main(config):\n    checks()\n    return animate({"scene": "' + scene + '", "temp": 35, "windy": True})\n')
        output = fixture.with_suffix(".webp")
        subprocess.run([os.environ.get("PIXLET", "pixlet"), "render", str(fixture), "-o", str(output)], check=True)
        with Image.open(output) as image:
            assert image.size == (64, 32), (scene, image.size)
            assert image.n_frames > 1, scene
print("All nine animated scenes and forecast checks passed.")
