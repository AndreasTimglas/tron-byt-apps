# USD SEK

A fixed 64×32 Tronbyt/Pixlet app showing **SEK per 1 USD**, the period change,
and a simple 7-day line chart. No API key, registration, OAuth, or secrets.
The MatrixPortal S3 displays the image rendered by the Tronbyt server.

## Run

From the repository root, with Tronbyt Pixlet v0.54.0 or newer:

```sh
pixlet check apps/usdsek/usdsek.star
pixlet render apps/usdsek/usdsek.star
pixlet serve apps/usdsek/usdsek.star
```

There are no settings: the pair is always USD → SEK. `USD>SEK` above `9.52`
means **1 USD = 9.52 SEK**. The rate and percentage sit together in a centered row with a four-pixel gap.
The rate has two decimal places; percentage change
has one decimal place and an explicit sign. `7D` labels the comparison.
The chart occupies the bottom 16 rows and all 64 columns. A dim dotted line marks the starting rate, without a full grid or
axes; its white endpoint marks the latest available observation.

## Data source and refresh

[Frankfurter v2](https://frankfurter.dev/) supplies keyless reference rates.
The request explicitly selects the ECB provider, not the default blended data:

```text
https://api.frankfurter.dev/v2/rates?base=USD&quotes=SEK&providers=ecb&from=YYYY-MM-DD&to=YYYY-MM-DD
```

One time-series request supplies both history and the latest available rate.
The window contains today in UTC and the preceding 6 calendar days. Rows are
sorted and filtered to that window; a preceding business-day row returned by
the API is excluded. Weekends and holidays without observations are normal.
The latest actual observation is used; missing dates are not filled with zero.
Horizontal spacing follows calendar days and lines connect observations across
weekend/holiday gaps. If only one observation is available, show a point and
+0.0%; if none are available, show the error screen.

`recommendedInterval: 360` recommends a **6-hour** render interval in minutes.
This follows the official [currencyconverter manifest](https://github.com/tronbyt/apps/blob/main/apps/currencyconverter/manifest.yaml)
and [interval list](https://github.com/tronbyt/apps/blob/main/update_intervals.txt),
which the [update script](https://github.com/tronbyt/apps/blob/main/update_intervals_script.sh)
writes into manifests. Set/confirm 360 minutes in Tronbyt Manager if the host
or an existing app installation overrides that recommendation. HTTP responses
and fresh parsed data are cached for 21,600 seconds; this is separate from the
host's rendering schedule. These are reference rates, not real-time quotes.

## Change and chart scaling

Using the first and last available observations **inside the requested window**:

```text
change_percent = (latest_rate / oldest_rate - 1) * 100
```

The calculation uses the original rates before display rounding. Positive
means one USD buys more SEK. Rounded tiny negative changes can show `-0.0%`.

The chart computes `data_min`, `data_max`, their midpoint, and observed span:

- Span ≤ 1.0 SEK: display midpoint − 0.5 through midpoint + 0.5.
- Span > 1.0 SEK: add 20% of the observed span below the minimum and above the maximum.

Thus 9.45–9.57 displays against 9.01–10.01, while 8.00–10.00 displays against
7.60–10.40. Flat data has a safe 1.0 SEK range, without division by zero.
Small movements can share a pixel row in this deliberately low-resolution
chart; the numeric percentage provides finer detail without exaggeration.

## Errors and caching

Non-200 HTTP responses, malformed JSON, empty data, and invalid rate rows are
handled. Pixlet's normal `cache.star` stores a successful response for up to
seven days. Fresh entries avoid another request for six hours. On an HTTP/data
failure, usable cached observations still within the current 7-day window
are shown with an asterisk (`USD>SEK 7D*`) and an amber change label. Without usable
cached data, a compact `USD>SEK / NO DATA` screen is displayed. Cache persistence
depends on the host; independent CLI runs need not share a persistent cache.

**Runtime limitation:** Pixlet v0.54.0's `http.get` raises fatal evaluation errors
for DNS, TLS, connection and timeout failures. Starlark has no supported catch
API or `try/except`, so these failures cannot trigger an app-level fallback.
The host must handle them. Cached fresh entries can render without a request,
but once refresh is due a transport failure remains host-handled. Full custom
transport-error handling requires runtime support; this app does not claim to
provide it.

## Validation

Checked official Tronbyt currencyconverter loading, HTTP/cache, manifest and
interval conventions, and Pixlet's documented Line/Stack/Text widgets.
Validated using Pixlet v0.54.0:

- `pixlet check apps/usdsek/usdsek.star` and live Frankfurter rendering.
- Empty schema output, requiring no configuration.
- Deterministic assertions for sorted weekend gaps, out-of-window filtering,
  invalid/zero rates, percentage direction, and fixed decimal formatting.
- Narrow, identical, and >1 SEK chart ranges; single-point, cached/stale, and
  empty-data screen rendering.

The existing OpenMeteo app is independent and unchanged.
