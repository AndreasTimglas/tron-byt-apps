# Daylight Compare

A 64×32 Tronbyt/Pixlet app comparing today's daylight and solar elevation
in two locations. Defaults: Malmö, Sweden, and Morristown, New Jersey.
No network service, API key, or Pi companion server is needed.

## Display

- Top left: Swedish flag, sunrise (up arrow) and sunset (down arrow).
- Top right: sunrise and sunset with the US flag.
- Times are local 24-hour HH:MM, with sunrise above sunset.
- Blue/yellow curve: Swedish location. Red/white/blue curve: US location.
- Bottom axis: local clock hours, cropped from one hour before the earliest
  sunrise to one hour after the latest sunset, rounded outward to whole hours.
  Polar conditions or daylight crossing midnight use the full 00–24 axis.
- Height: solar elevation, using the same scale for both curves.

Each curve uses its city's own local time, **not simultaneous UTC time**.
The curves therefore compare the shape and length of the local day. Each city
uses its own current calendar date. Sunrise and sunset are converted separately
to the selected timezone, including the DST offset at each event.
The shared vertical scale adjusts seasonally to use the available pixels;
heights are comparable within a screen, but not between screenshots from
separate seasons. Only the daylight portion is drawn. Overlapping curve pixels
alternate between the two countries so neither curve completely hides the other.

Daylight is estimated sunrise-to-sunset time, **not cloud-free sunshine**.
Event times use Pixlet's built-in `sunrise.star`, the same calculator as the
[official Sunrise Sunset app](https://github.com/tronbyt/apps/blob/main/apps/sunrisesunset/sunrise_sunset.star).
Labels use the same HH:MM formatting (seconds are omitted, not rounded).
Day length for fireworks is the elapsed time between the events before formatting.
The graph retains the approximate NOAA elevation shape, aligned to the calculated
sunrise and sunset endpoints. Terrain, buildings, and actual atmospheric
conditions are not modeled. Polar day/night show --:-- when no event occurs;
the NOAA approximation supplies the polar day-length fallback.

## Install and configure

Refresh this custom repository in Tronbyt Manager and add **Daylight Compare**.
Choose **Swedish location** and **US location**, or leave them unset to use the
defaults. Both fields use `schema.Location` latitude, longitude, and timezone.
The flags follow the field roles; they do not change automatically by country.
Invalid coordinates or missing timezone values show SET CITY. Timezone names
must be valid IANA names as supplied by the location picker.

Recommended render interval: **60 minutes**. Suggested display time: **5 seconds**.
Normally the app is static. When calculated day lengths differ by **two minutes
or less**, small flag-colored fireworks overlay the plot in a four-second loop.
The comparison uses unrounded durations, not rounded sunrise/sunset labels.
Flags, event times, and hour labels remain clear. Full-animation playback is not
forced, so the configured display time can still control app rotation.

## Local development

Use Tronbyt Pixlet v0.54.0 or newer. From this folder:

```sh
pixlet check daycompare.star
pixlet render daycompare.star
pixlet serve daycompare.star
```

Example location override:

```sh
pixlet render daycompare.star 'sweden={"lat":"59.3293","lng":"18.0686","timezone":"Europe/Stockholm"}'
```

Validated with Tronbyt Pixlet v0.54.0: check, default render, and deterministic
checks for equatorial equinox, both poles in summer/winter, seasonal day-length
ordering, timezone shifts, leap day, duration formatting, and invalid coordinates.

Regression checks compare both cities against the official app's event calls
for October 15, both 2026 spring DST transition dates, and both solstices.
Check both location fields in Manager: saved values override the code defaults.
If both fields select the same city, their times will correctly be identical.
