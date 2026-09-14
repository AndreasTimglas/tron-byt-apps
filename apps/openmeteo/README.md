# Open-Meteo Weather for Tronbyt

A static, exactly 64×32 Pixlet weather app. Celsius only, no scrolling,
credentials, API keys, or external image assets.

## Run

Use [Tronbyt Pixlet](https://github.com/tronbyt/pixlet/releases) v0.54.0 or newer:

```sh
pixlet check openmeteo.star
pixlet render openmeteo.star
pixlet serve openmeteo.star
```

An unconfigured render shows `SET LOCATION`. In the served configuration UI
or Tronbyt Manager, choose **Location**. The app reads the schema's JSON value
(`lat`, `lng`, `timezone`), using `auto` only if its timezone is empty.
For a command-line render with a location:

```sh
pixlet render openmeteo.star 'location={"lat":"59.3293","lng":"18.0686","timezone":"Europe/Stockholm"}'
```

Keep `openmeteo.star` and `manifest.yaml` together when adding the app
to your custom Tronbyt app source. Select Location in Manager after adding it.
The manifest is custom-app metadata; publishing to the community catalog may
also require a preview image and repository submission metadata.

## Display

The static 64×32 layout uses 42 pixels for **TODAY**, a one-pixel divider,
and 21 pixels for **TMRW**. The compact bitmap labels keep both days visible
without scrolling.

- Today: current condition icon and temperature in °C; high (`H`) and low
  (`L`); feels-like (`F`) and relative humidity (`H%`); droplet plus today's
  maximum precipitation probability.
- Tomorrow: daily condition icon, high (`H`), low (`L`), and droplet plus
  tomorrow's maximum precipitation probability.

All temperature readings are Celsius. Humidity and precipitation probability
are different measures; `H%65` means 65% relative humidity. Temperatures round
to whole degrees, with halves rounded away from zero. Missing readings show
`--`, and missing/unknown condition codes show `?`.

The daily arrays supply today at index 0 and tomorrow at index 1, in the
selected location's timezone. Tomorrow's icon represents its daily weather
code; today's icon represents the current weather. Clear conditions use the
sun graphic even at night because day/night information is not requested.

The smaller auxiliary labels trade some distance readability for simultaneous
access to both days. The icons and current temperature remain larger.

## Data and failure handling

The [Open-Meteo forecast API](https://open-meteo.com/en/docs) receives:

- Current: `temperature_2m,relative_humidity_2m,apparent_temperature,weather_code`
- Daily: `temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code`
- `temperature_unit=celsius`, `forecast_days=2`, and the configured timezone.

Daily values refer to today and tomorrow in the selected timezone. Each blue
droplet shows that day's maximum probability, not an instantaneous probability.
Responses are cached for 600 seconds. Schedule refreshes about every 10 minutes.
Successful render roots carry `max_age=1800` as a host/device expiration hint.

Missing or malformed location configuration, non-200 HTTP responses, invalid
JSON, API errors, and absent core data produce compact readable error screens.

**Pixlet limitation:** v0.54.0 propagates DNS, connection, and timeout failures
from `http.get` as fatal evaluation errors. Its Starlark runtime has no
`try/except` or supported catch API, so a standalone app cannot render its own
error screen for those transport failures. They must be handled by the host;
the app does not fabricate weather or promise a local fallback. Fully custom
transport-error screens would require a Pixlet runtime change.

## Compatibility and validation

Implementation patterns were checked against the official
[weatherclock app](https://github.com/tronbyt/apps/blob/main/apps/weatherclock/weatherclock.star),
[weatherdashboard app](https://github.com/tronbyt/apps/blob/main/apps/weatherdashboard/weather_dashboard.star),
[Location example](https://github.com/tronbyt/pixlet/blob/main/docs/schema/location/example.star),
and [widget documentation](https://github.com/tronbyt/pixlet/blob/main/docs/widgets.md).
The HTTP response accessor is `response.body()`; malformed JSON is handled
with `json.decode(..., default=None)`, both verified against the current runtime.

Validated with Tronbyt Pixlet v0.54.0: `pixlet check`, live Open-Meteo rendering,
unconfigured and invalid-location screens, and synthetic weather renders for
negative temperatures, 100% readings, and missing tomorrow data. The layout uses built-in bitmap fonts
and original pixel graphics, without unsupported drawing or exception APIs.

Weather data by [Open-Meteo](https://open-meteo.com/), under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
