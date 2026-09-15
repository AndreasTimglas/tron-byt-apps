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
source = (ROOT / "apps/annaflowers/annaflowers.star").read_text()
source = source.replace("def main(config):", "def original_main(config):")
samples = ["Anna", "Anna, Anna, vad gör man en söndagmorgon", "W" * 120, "Malmö " * 15]
with tempfile.TemporaryDirectory() as directory:
    for index, text in enumerate(samples):
        script = Path(directory) / "fixture.star"
        script.write_text(source + "\ndef main(config):\n    return flower_screen(" +
                          json.dumps(text, ensure_ascii=False) + ")\n")
        subprocess.run([pixlet, "render", str(script)], check=True, capture_output=True)
        js = (HERE / "font.js").read_text() + (HERE / "layout.js").read_text() + (HERE / "flowers.js").read_text()
        js += "\nconst text=" + json.dumps(text) + ";const n=boardWidth(text)<=46?1:boardWidth(text)+46;"
        js += 'console.log(JSON.stringify(Array.from({length:n},(_,p)=>flowerPixels(text,"#ffffff",p))));'
        pages = json.loads(subprocess.check_output(["node", "-e", js]))
        image = Image.open(script.with_suffix(".webp"))
        assert image.size == (64, 32)
        # Compare decoded animation against expected frames, allowing WebP to merge duplicates.
        frame_index = 0
        for page in range(image.n_frames):
            image.seek(page)
            rgb = image.convert("RGB")
            pixels = pages[frame_index]
            expected = {(x,y): tuple(bytes.fromhex(color[1:])) for x,y,color in pixels}
            actual = {(x,y): rgb.getpixel((x,y)) for y in range(32) for x in range(64) if rgb.getpixel((x,y)) != (0,0,0)}
            assert actual == expected, (index, page, frame_index, "Preview differs from Pixlet")
            delay = 60 if len(pages) == 1 else min(60, 14000 // len(pages))
            frame_index += max(1, round(image.info.get("duration", delay) / delay))
print("Flower preview parity passed for", len(samples), "messages.")
