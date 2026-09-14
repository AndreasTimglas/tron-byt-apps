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

The default 64×32 view uses two balanced 31-pixel columns separated by a
2-pixel divider. Each has four generously spaced rows:

- **TODAY / TMRW** heading.
- Condition icon; today also shows the current temperature in °C.
- High / low temperatures: warm-colored high, blue low, separated by `/`.
- Blue droplet and precipitation probability in percent.

All temperatures are Celsius. Tomorrow uses its daily condition code, while
today uses the current code. Both daily forecasts follow the selected location's
timezone. Missing values show `--` and missing condition codes show `?`.

**Show extra details** is off by default. Enable it in Manager to restore the
denser 42/21-pixel layout with current feels-like (`F`) and relative humidity
(`H%`) as well as the two-day forecast. The compact view prioritizes readability;
the detailed view fits more information with smaller, tightly spaced labels.
Humidity is distinct from precipitation probability.

Temperatures round to whole degrees, with halves rounded away from zero.
The sun graphic indicates clear conditions, including at night, because no
day/night field is requested.

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
