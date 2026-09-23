# GIF Slideshow

Upload GIFs at http://tidbyt-pi.local:8787/gifs using the existing Pi message
service. No cloud storage or credentials are required.

## Install

On the Pi:

~~~sh
cd ~/tronbyt-messages
git pull --ff-only
cd services/messageboard
docker compose up -d --build
~~~

Refresh your custom repository in Tronbyt Manager and add **GIF Slideshow**.
Set **GIF server** to http://192.168.0.127:8787 (use your Pi's current IP).
Set render interval to **0 (every time)**, **Display Time to 1 second**,
and **Show Full Animation to True**. The complete animation then provides
the selected 5, 10 or 15 seconds. Firmware must support full-animation playback;
device timing and network delays can add some time. A longer Display Time
can keep a GIF on screen longer than the web setting.

Each render advances to the next GIF. A Manager preview, an extra render or
another device using this same playlist also advances its shared cursor.
This is render-based rotation, not an acknowledgement from the physical
display. Rendering at a fixed interval can reuse a GIF between renders.
A render failure after selection may skip an item until the next loop.

## Upload and preview

- Fit preserves the whole image, adding black borders; Crop fills the display
  by trimming the centered image.
- Converted previews and display use the same 64×32 frames with original frame timing.
- Select 5, 10 or 15 seconds for every GIF. Short GIFs loop; longer loops
  stop at the selected duration. There is no audio.
- Move up/down sets playlist order. Editing the order or removing an entry
  resets the cursor to the beginning.
- An empty playlist returns no content and is skipped by Tronbyt.
- Uploads: GIF only, maximum 8 MB, one megapixel, 300 frames, 30-second loop.
  Maximum 30 active GIFs and 512 MB total stored files.
- Originals, normalized frames, playlist and cursor persist in the existing
  Docker volume under /data/gifs. Do not copy files directly into this folder:
  upload through the web page so validation and conversion are applied.
- Remove takes a GIF out of rotation and makes it unavailable through the API.
  Its files remain in the volume for manual recovery, and count toward the
  storage limit.

~~~sh
pixlet check apps/gifslideshow/gifslideshow.star
pixlet render apps/gifslideshow/gifslideshow.star server=http://192.168.0.127:8787
pixlet serve apps/gifslideshow/gifslideshow.star
~~~

Transport errors remain host-handled. GET /api/gifs/next intentionally advances
the shared playlist; listing and preview endpoints never advance it.

Original per-frame delays are preserved; missing, zero and 10 ms GIF delays
use a browser-style 100 ms fallback. Existing uploads are rebuilt automatically
from stored originals. Update both the Pi service and the Pixlet app for this
timing support. Playback duration controls how long a GIF stays, not its speed.
