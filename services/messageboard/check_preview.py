"""Compare browser preview pixels to real Pixlet output. Requires Node and Pillow."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
pixlet = sys.argv[1] if len(sys.argv) > 1 else "pixlet"
source = (ROOT / "apps/messageboard/messageboard.star").read_text()
source = source.replace("def main(config):", "def original_main(config):")
samples = [
    "Welcome to Malmö!", "There is a present under the bed",
    "W" * 120, "i" * 120,
    "Anna, Anna, vad gör man en söndagmorgon",
    " ".join(chr(i) for i in range(32, 90)),
    " ".join(chr(i) for i in range(90, 127)),
    " ".join(chr(i) for i in range(160, 208)),
    " ".join(chr(i) for i in range(208, 256)),
]
with tempfile.TemporaryDirectory() as directory:
    for index, text in enumerate(samples):
        script = Path(directory) / "fixture.star"
        script.write_text(source + "\ndef main(config):\n    return message_screen(" +
                          json.dumps({"text": text, "display_color": "#ffffff"}, ensure_ascii=False) + ")\n")
        subprocess.run([pixlet, "render", str(script)], check=True, capture_output=True)
        js = (HERE / "font.js").read_text() + (HERE / "layout.js").read_text()
        js += "\nconst lines=boardLines(" + json.dumps(text) + ");"
        js += "const n=Math.ceil(lines.length/3);console.log(JSON.stringify(Array.from({length:n},(_,p)=>boardPixels(lines.slice(p*3,p*3+3),p,n))));"
        pages = json.loads(subprocess.check_output(["node", "-e", js]))
        image = Image.open(script.with_suffix(".webp"))
        assert image.size == (64, 32)
        assert image.n_frames == len(pages), (index, image.n_frames, len(pages))
        for page, pixels in enumerate(pages):
            image.seek(page)
            rgb = image.convert("RGB")
            expected = {(x, y): (255 if active else 34) for x, y, active in pixels}
            actual = {(x, y): rgb.getpixel((x, y))[0] for y in range(32) for x in range(64) if rgb.getpixel((x, y))[0]}
            assert actual == expected, (index, page, "Preview differs from Pixlet")
print("Pixel-for-pixel preview parity passed for", len(samples), "messages.")
