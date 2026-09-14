# City Flip

A 64×32, 24-hour clock with a small city label above four large split-flap-style
digits. Defaults to **Malmö**, using **Europe/Stockholm** (including daylight
saving time). No API keys or external weather/time requests.

## Run

From the repository root with Tronbyt Pixlet v0.54.0 or newer:

```sh
pixlet check apps/cityflip/cityflip.star
pixlet render apps/cityflip/cityflip.star
pixlet serve apps/cityflip/cityflip.star
```

Select **Location** in Tronbyt Manager to choose another timezone and city.
The optional **City label** overrides the displayed name without changing the
timezone. For example:

```sh
pixlet render apps/cityflip/cityflip.star 'location={"locality":"Malmö","timezone":"Europe/Stockholm"}'
```

## Layout and time

The city occupies the top 8 rows in small `tb-8` text, preserving the umlaut in
Malmö. Labels longer than 10 characters are shortened with a period; use the
City label setting for a preferred abbreviation. The clock occupies the bottom
24 rows: four 13×24 gray cards with white `10x20` digits, a dark horizontal hinge,
and a subtle colon. The 59-pixel clock row is centered. There is no AM/PM or
scrolling. Leading zeros are retained, e.g. **00:08** and **09:05**.

This is a **static flip-style design**, not a flap animation. Time is evaluated
at each render on the Tronbyt server, using the configured location timezone.
The manifest recommends a one-minute refresh (`recommendedInterval: 1`, in
minutes). Confirm that interval in Manager. Refresh scheduling may not fall
exactly on the minute boundary. The root includes a 90-second expiration hint;
actual expiry behavior depends on the host/device. The image does not advance
time independently while offline.

Malformed location JSON shows SET CITY. The Location picker provides valid IANA
timezones; a manually entered invalid timezone is a Pixlet runtime error.

## Validation

Validated with Pixlet v0.54.0: formatting, `pixlet check`, default Malmö render,
and fixed-time renders covering midnight, leading zeros, and 23:59.
Uses the established schema.Location / time.now().in_location() pattern and
built-in Text, Box, Padding, Row, Column, and Stack widgets.
