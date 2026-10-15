# Weather Play

An original 64×32 animated weather world for Tronbyt. Uses the next three
hourly forecast points from Open-Meteo, with no API key or companion server.

## Install

Refresh your custom app repository in Tronbyt Manager, add **Weather Play**,
and select **Location**. Suggested render interval: **10 minutes**. Set display
time to **8 seconds** to see the 7.2-second loop. Shorter display times are
allowed; the app does not force complete animation playback.

The header shows NEXT 3H and the **highest Celsius temperature** among the
three forecast points. Times are selected using Unix timestamps, so midnight
and daylight-saving changes do not create ambiguous comparisons. The selected
location's latitude, longitude, and timezone are sent to Open-Meteo.

## Scenes

| Scene | Trigger and animation |
| --- | --- |
| Thunderstorm | WMO 95/96/99: rain, duck, and occasional small lightning bolts |
| Snow | WMO 71/73/75/77/85/86: falling snow, snowbanks, snowman and escaping hat |
| Rain | Drizzle, rain, freezing rain and shower codes: splashes, rising/receding pool, floating duck |
| Heat | Forecast maximum at least 30°C: flames and embers; taller flames up to 37°C |
| Wind | Sustained wind at least 25 km/h or gusts at least 40 km/h: bending tree, leaves and runaway umbrella |
| Fog | WMO 45/48: mist passing a streetlamp |
| Night | All three forecast points are after dark: moon and twinkling stars |
| Cloudy | WMO 2/3: clouds drifting over the sun and flower |
| Sunny | Otherwise: sun wearing sunglasses and opening flower |

The first matching row wins. Wind also slants rain, drifts snow, and bends
flames. Thresholds are design choices, not official weather-warning levels.
Water depth and snow accumulation are storytelling effects, not quantitative
predictions. The scene represents conditions expected somewhere in the next
three hours, not a minute-by-minute forecast timeline.

All graphics are drawn directly with Pixlet pixels; no GIF downloads, fonts,
image services or generated art are required. A 48-frame loop runs at 150 ms
per frame. Everything is clipped to the 64×32 canvas, with a protected header.

## Data and errors

[Open-Meteo](https://open-meteo.com/en/docs) hourly variables:
`temperature_2m,weather_code,wind_speed_10m,wind_gusts_10m,is_day`.
Requests use Celsius, km/h, Unix timestamps, and two forecast days so the
three-hour window works over midnight. Responses are cached for ten minutes;
rendered forecasts have a 30-minute maximum-age hint.

Missing location, malformed coordinates, HTTP errors, malformed JSON, missing
hours or null forecast values produce a small error screen. As with the other
apps, Pixlet v0.54.0 cannot catch transport exceptions (DNS/connection/timeout);
Tronbyt Manager handles those render failures.

Data attribution: Weather data by [Open-Meteo](https://open-meteo.com/),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The free API is intended for non-commercial use.

## Development

Use Tronbyt Pixlet v0.54.0 or newer, from this directory:

```sh
pixlet check weatherplay.star
pixlet render weatherplay.star
pixlet serve weatherplay.star
```

An unconfigured render shows SET CITY. For a live Morristown render:

```sh
pixlet render weatherplay.star 'location={"lat":"40.7968","lng":"-74.4815","timezone":"America/New_York"}'
```

Repeatable tests (Python 3 and Pillow):

```sh
PIXLET=/path/to/pixlet python3 test_weatherplay.py
```

Tests cover weather codes, precedence, heat/wind thresholds, night selection,
time-window boundaries, missing data and coordinates, and animated 64×32
renders of all nine scenes. A live Morristown forecast was also rendered.
