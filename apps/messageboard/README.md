# Message Board

Display messages sent from the iPhone-friendly web page running on your Pi.
See [receiver setup and Pi installation commands](../../services/messageboard/README.md).

~~~sh
pixlet check apps/messageboard/messageboard.star
pixlet render apps/messageboard/messageboard.star server=http://192.168.0.127:8787
pixlet serve apps/messageboard/messageboard.star
~~~

Configure **Message server** with the Pi's actual LAN IP and port 8787.
The recommended refresh is one minute; set the display duration to 15 seconds.

Messages use the chosen color and readable tb-8 text, up to three lines per
page. Widths are measured in pixels; long words are split without dropping
characters. Pages advance every three seconds, or slightly faster when needed
to keep the entire message under Pixlet's 15-second animation limit.

There is no HTTP caching. Clear, replacements, and expiry take effect on the
next host render. Empty/expired messages return no content, so Tronbyt skips this app. A missing server URL
shows SET URL. HTTP/data errors show NO SERVER. The root includes a maximum-age
hint of 60 seconds (or remaining expiry, if sooner); device enforcement varies.
Transport errors remain host-handled because Pixlet has no supported catch API.

The service stores up to 120 Latin-1 characters and converts smart punctuation
from phone keyboards. The display does not show arbitrary HTML or run code
from messages. No credentials are required. This is a trusted-LAN application,
not a public messaging endpoint.

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
