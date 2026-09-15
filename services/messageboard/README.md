# Message Board for iPhone and Tronbyt

A small web page on your Raspberry Pi: write a message in Safari, choose its
color, then tap **Send to display**. The companion Pixlet
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
- Every Send starts a one-hour rotation window. Sending again resets the hour.
- After expiry or Clear, the app is skipped on the next render (within about one minute).
- Restarting the service does not restart the hour; older saved messages are also capped at one hour.
- Clear removes the saved message. Sending another message replaces it.
- The phone preview is illustrative; Pixlet uses measured text widths to split
  the actual message into up to three lines per page, without scrolling.
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

The receiver uses only Python's standard library. Its endpoints are:

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
python3 services/messageboard/server.py --host 127.0.0.1 --data /tmp/board/message.json
python3 -m unittest discover -s services/messageboard -v
pixlet check apps/messageboard/messageboard.star
pixlet render apps/messageboard/messageboard.star server=http://127.0.0.1:8787
~~~

Validated: nine backend tests covering persistence, one-hour expiry and replacement, normalization,
invalid input, failed saves, request protections and file routing; JavaScript
syntax and Compose configuration; browser send/color/expiry/clear at desktop
and iPhone-sized viewports; Pixlet live API rendering and pagination of long
words and Swedish text.

The Docker daemon was unavailable on the development Mac, so the container
build/run still needs to happen on the Pi using the installation commands.
Pi installation was not attempted after SSH authentication was rejected.
