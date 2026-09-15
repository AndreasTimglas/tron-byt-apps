# Anna Flowers

Write a message at http://tidbyt-pi.local:8787/flowers and send it to scroll
inside the existing flower border. The composer has its own messages,
independent of Message Board, with color and expiry choices.

Update the Pi service using the [installation guide](../../services/messageboard/README.md).
In Tronbyt Manager refresh your custom repository, configure Anna Flowers'
**Message server** as http://192.168.0.127:8787 (your Pi's actual IP),
and set render interval to **1 minute**, display duration to **15 seconds**.
Leave Message server empty to keep the original fixed Anna greeting.

Messages allow up to 120 characters including Swedish letters. Short text is
centered; longer text scrolls continuously, without pagination. Long messages
scroll faster so the complete loop fits within 14 seconds.
The browser preview uses the same glyphs, border, scroll coordinates and speed.

Send starts the chosen expiry timer. Clear or expiry skips the configured app
on the next render. Updates appear at the next render and normal app rotation.
HTTP/data errors skip the app; transport errors remain host-handled.

~~~sh
pixlet check apps/annaflowers/annaflowers.star
pixlet render apps/annaflowers/annaflowers.star
pixlet serve apps/annaflowers/annaflowers.star
~~~
