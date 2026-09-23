# Message Board for iPhone and Tronbyt

A small web page on your Raspberry Pi: write a message in Safari, choose its
color and time limit, then tap **Send to display**. The companion Pixlet
app displays it on its next scheduled render.

## Install on the Pi

Log in to the Pi normally, then run:

~~~sh
git clone https://github.com/AndreasTimglas/tron-byt-apps.git ~/tronbyt-messages
cd ~/tronbyt-messages/services/messageboard
docker compose up -d --build
docker compose ps
~~~

This is a separate service on port 8787, not a modification of your Tronbyt
server. It uses the Pi's existing Docker installation. If your account needs
sudo for Docker, prefix the Docker commands with sudo.

On your iPhone, connected to your home Wi-Fi, open:

**http://tidbyt-pi.local:8787**

Fallback: **http://192.168.0.127:8787** (if that is still your Pi's IP).
In Safari, use **Share → Add to Home Screen** for convenient access.

If the clone folder already exists, use this update procedure instead:

~~~sh
cd ~/tronbyt-messages
git pull --ff-only
cd services/messageboard
docker compose up -d --build
~~~

## Add the display app

1. Refresh the Custom Apps Repository in Tronbyt Manager.
2. Add **Message Board**.
3. Set **Message server** to http://192.168.0.127:8787, using the Pi's actual
   LAN IP. An IP is preferable when Tronbyt runs in Docker because .local
   resolution is not always available inside containers.
4. Set its refresh interval to **1 minute** and display duration to **15 seconds**.
5. Enable the app and save. Send a message from your iPhone.

A successful Send means the Pi saved the message; it is not a delivery
acknowledgement from the LED matrix. The message appears on the next render
and app rotation. This service does not interrupt or pin the app, and needs no
Tronbyt credentials. Expiry and Clear also take effect on the next render.
When no message is active, Tronbyt skips the app. Leave it enabled so it keeps checking for new messages.

## Features

- Up to 120 characters, with color choices: white, green, yellow, pink.
- Latin-1 text including Swedish å, ä, ö. Smart quotes/dashes from the iPhone
  keyboard are converted to their simple equivalents. Emoji are rejected with
  a helpful message because the display font cannot reliably show them.
- Choose 5, 15, or 30 minutes; 1, 3, 6, or 24 hours. The default is 1 hour.
- Every Send starts a new rotation window for the selected duration.
- After expiry or Clear, the app is skipped on the next render (within about one minute).
- Restarting the service preserves the expiry time. Legacy messages without an expiry are capped at one hour.
- Clear removes the saved message. Sending another message replaces it.
- The phone preview uses the same tb-8 pixel glyphs, wrapping, centered alignment,
  margins and page indicators as Pixlet. Every page is shown before sending.
- Saved data survives service/Pi restarts in the Docker volume.
- There is no email, SMS provider, API key, account, or subscription.

## Network scope

This is for a **trusted home LAN**. There is no login: anyone on that network
who can reach the service can read, replace, or clear messages. Do not expose
port 8787 to the public Internet. It uses plain HTTP on the LAN.

Writes require same-origin JSON, and an explicit hostname/IP allowlist blocks
cross-site requests and DNS rebinding. This is request protection, not user
authentication. The page has no third-party resources or analytics. Messages
are inserted as text, never HTML. Logs omit message contents.

The default allowed addresses are localhost, 127.0.0.1, tidbyt-pi.local and
192.168.0.127. If your Pi has a different IP, create a .env file in this
directory with its actual address included:

~~~text
BOARD_ALLOWED_HOSTS=localhost,127.0.0.1,tidbyt-pi.local,192.168.0.50
~~~

Then rerun docker compose up -d. The .env file is ignored by Git. Use that
same IP for the Message server setting. The app does not require HTTPS on the
local network; adding it to the iPhone Home Screen is optional.

## Maintenance

~~~sh
cd ~/tronbyt-messages/services/messageboard
docker compose logs --tail=50
docker compose restart
docker compose down
~~~

The final command stops the service but preserves messages. Do not add -v
unless you intend to delete the saved data.

The message receiver uses Python's standard library; GIF conversion additionally uses Pillow. Its endpoints are:

- GET /: phone interface.
- GET /api/message: current message and expiry information.
- POST /api/message: save a JSON object with text, color, expires_minutes.
- POST /api/clear: clear with an empty JSON object.
- GET /health: service health.

State is atomically saved before a successful response. Expired text is not
returned by the API; it remains in the local data file until cleared or replaced.
The container runs as a non-root user, with a read-only filesystem except its
data volume, and restarts automatically after reboot.

## Local development and validation

~~~sh
python3 -m pip install -r services/messageboard/requirements.txt
python3 services/messageboard/server.py --host 127.0.0.1 --data /tmp/board/message.json
python3 -m unittest discover -s services/messageboard -v
pixlet check apps/messageboard/messageboard.star
pixlet render apps/messageboard/messageboard.star server=http://127.0.0.1:8787
~~~

Validated: ten backend tests covering persistence, all seven time limits, expiry and replacement, normalization,
invalid input, failed saves, request protections and file routing; JavaScript
syntax and Compose configuration; browser send/color/expiry/clear at desktop
and iPhone-sized viewports; Pixlet live API rendering and pagination of long
words and Swedish text.

The Docker daemon was unavailable on the development Mac, so the container
build/run still needs to happen on the Pi using the installation commands.
Pi installation was not attempted after SSH authentication was rejected.

### Preview and page capacity

Each page holds three lines of up to 60 pixels, with each line centered horizontally.
There is no fixed character cutoff: wide letters and word breaks use more room.
The editor shows the actual line/page count and all pages so you can shorten
a message before sending. Total input remains limited to 120 characters.
Update both the web service and the Message Board app in Tronbyt Manager to
keep the preview and display aligned.

The preview font is derived from Pixlet’s public-domain tb-8 BDF.
Pixel parity can be checked with Node, Pillow and Pixlet installed:

~~~sh
python3 services/messageboard/check_preview.py /path/to/pixlet
~~~

## Anna Flowers composer

Open **http://tidbyt-pi.local:8787/flowers** or use the Anna Flowers link.
It shares this service but saves messages separately in flowers.json in the
same persistent volume. The normal Message Board is unaffected.

Configure Anna Flowers in Tronbyt Manager with the same Message server URL,
a 1-minute refresh and a 15-second display duration. Update the custom apps
repository to get the new configuration field. Without a URL, Anna Flowers
keeps its original greeting. With a URL, it shows only active flower messages.

The composer previews the flower border and scrolling pixel text. It supports
the same colors, 120-character limit, expiry choices and Clear button.

## Schedule messages

Both composers offer **Show now** or **Schedule**. Choose a start date/time
and end date/time, then save. All scheduling and displayed timestamps use
**America/New_York**, independent of your phone or Pi timezone. Each schedule
is one-off; daylight-saving times that do not exist or occur twice are rejected
with an explanation. Normal dates automatically use EST or EDT.

The scheduled-message list supports editing and cancelling upcoming or active
windows. Overlapping windows are rejected per app, but Message Board and Anna
Flowers can each have their own schedules. Up to 100 pending windows per app
are supported. Adjacent windows (one ends as another starts) are allowed.

The Pi stores windows atomically alongside the current message in its existing
Docker volume. It selects the active window whenever the display fetches data;
no open browser, cron task or extra worker is needed. Restarting during a
window resumes it; restarting after its end never replays it.

A scheduled message replaces any Show now message at its start; the earlier
message does not resume. Show now is rejected while a scheduled message is
active: cancel it first to replace it. Clear stops the current message and
keeps future schedules. Cancelling a schedule removes only that window.

Keep each Tronbyt app enabled with a **1-minute render interval**. Start/end
changes take effect at the next render and normal rotation; they are not
second-exact interruptions. These are normal rotation windows, not screen pins.

Additional endpoints (same request protection as Send):
- POST /api/message/schedule or /api/flowers/schedule:
  text, color, start and end as YYYY-MM-DDTHH:MM; optional id edits a window.
- POST /api/message/cancel or /api/flowers/cancel: id.
- GET on each existing message endpoint includes schedules and scheduled status.

Update the Pi service with git pull --ff-only and docker compose up -d --build,
then reload the page. No display-app update is required for scheduling.
The Docker image includes tzdata for New York daylight-saving rules.


## GIF Slideshow

The **GIF Slideshow** navigation link opens /gifs. Upload, preview, reorder
and remove GIFs there; choose 5, 10 or 15 seconds of playback. Fit adds black
borders and Crop fills the matrix. Data is kept under /data/gifs in the same
Docker volume. Removing a GIF hides it from the playlist; its files are
retained for manual recovery.

See [the slideshow setup guide](../../apps/gifslideshow/README.md) for required
Tronbyt render/display settings and limits. Each render (including a Manager
preview) advances the shared playlist. The web page never advances it.

GIF conversion uses Pillow, installed during the Docker build. For local
development, install requirements.txt before running the service or tests.
