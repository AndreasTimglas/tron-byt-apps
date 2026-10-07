# Daylight Compare

A 64×32 Tronbyt/Pixlet app comparing today's daylight and solar elevation
in two locations. Defaults: Malmö, Sweden, and Morristown, New Jersey.
No network service, API key, or Pi companion server is needed.

## Display

- Top left: Swedish flag and daylight duration in hours:minutes.
- Top right: daylight duration and US flag.
- Blue/yellow curve: Swedish location. Red/white/blue curve: US location.
- Bottom axis: local clock hours, cropped from one hour before the earliest
  sunrise to one hour after the latest sunset, rounded outward to whole hours.
  Polar conditions or daylight crossing midnight use the full 00–24 axis.
- Height: solar elevation, using the same scale for both curves.

Each curve uses its city's own local time, **not simultaneous UTC time**.
The curves therefore compare the shape and length of the local day. Each city
uses its own current calendar date and timezone offset at render time, including
DST. On a clock-change day, the plot uses that single offset for the entire day.
The shared vertical scale adjusts seasonally to use the available pixels;
heights are comparable within a screen, but not between screenshots from
separate seasons. Only the daylight portion is drawn. Overlapping curve pixels
alternate between the two countries so neither curve completely hides the other.

Daylight is estimated sunrise-to-sunset time, **not cloud-free sunshine**.
The calculation follows the [NOAA fractional-year solar equations](https://gml.noaa.gov/grad/solcalc/solareqns.PDF),
with a -0.833° sunrise/sunset threshold for standard refraction and the solar
disc. Terrain, buildings, and actual atmospheric conditions are not modeled.
Durations are rounded to minutes; they are approximate, not observational
measurements. Polar day/night show 24:00 or 0:00.

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
The comparison uses unrounded durations, not the displayed minute values.
Flags, durations, and hour labels remain clear. Full-animation playback is not
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
