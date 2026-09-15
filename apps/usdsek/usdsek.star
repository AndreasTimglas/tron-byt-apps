load("cache.star", "cache")
load("encoding/json.star", "json")
load("http.star", "http")
load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

URL = "https://api.frankfurter.dev/v2/rates"
CACHE_KEY = "usdsek-ecb-7d-v2"
PERIOD_DAYS = 7
CHART_HEIGHT = 16
REFRESH_SECONDS = 21600

def get_schema():
    return schema.Schema(version = "1", fields = [])

def error_screen():
    return render.Root(child = render.Box(width = 64, height = 32, child = render.Column(
        cross_align = "center",
        children = [render.Text("USD>SEK", color = "#66ddff"), render.Text("NO DATA", color = "#ffbb66")],
    )))

def observations(data, dates):
    if type(data) != "list":
        return []
    by_date = {}
    for row in data:
        if type(row) != "dict" or row.get("base") != "USD" or row.get("quote") != "SEK":
            continue
        date = row.get("date")
        rate = row.get("rate")
        if type(date) == "string" and date in dates and type(rate) in ["int", "float"] and rate > 0 and rate < 1000:
            by_date[date] = rate

    # Frankfurter may include a preceding business day: exclude it explicitly.
    # Calendar offsets retain weekend/holiday gaps on the horizontal axis.
    return [(i, by_date[date]) for i, date in enumerate(dates) if date in by_date]

def chart_bounds(values):
    low = min(values)
    high = max(values)
    spread = high - low
    midpoint = (low + high) / 2
    if spread <= 1.0:
        return (midpoint - 0.5, midpoint + 0.5)
    return (low - spread * 0.2, high + spread * 0.2)

def fixed(value, places):
    # Starlark has no Python-style floating-point format specifications.
    scale = 100 if places == 2 else 10
    rounded = int(abs(value) * scale + 0.5)
    fraction = str(rounded % scale)
    if places == 2 and len(fraction) == 1:
        fraction = "0" + fraction
    return str(rounded // scale) + "." + fraction

def percent_change(oldest, latest):
    return (latest / oldest - 1) * 100

def chart(points, color):
    low, high = chart_bounds([point[1] for point in points])
    coords = [(int(day * 63 / (PERIOD_DAYS - 1)), int((high - rate) * (CHART_HEIGHT - 1) / (high - low) + 0.5)) for day, rate in points]
    children = [render.Box(width = 64, height = CHART_HEIGHT)]

    # Dim baseline shows where the period began without adding a full grid.
    baseline = coords[0][1]
    for x in range(0, 64, 4):
        children.append(render.Padding(pad = (x, baseline, 0, 0), child = render.Box(width = 1, height = 1, color = "#333333")))
    for i in range(1, len(coords)):
        # Line normalizes its own bounds; explicitly place each segment.
        left = min(coords[i - 1][0], coords[i][0])
        top = min(coords[i - 1][1], coords[i][1])
        children.append(render.Padding(pad = (left, top, 0, 0), child = render.Line(
            x1 = coords[i - 1][0],
            y1 = coords[i - 1][1],
            x2 = coords[i][0],
            y2 = coords[i][1],
            width = 1,
            color = color,
            antialias = False,
        )))

    # Visible even if there is just one available observation.
    x, y = coords[-1]
    children.append(render.Padding(pad = (x, y, 0, 0), child = render.Box(width = 1, height = 1, color = color)))
    return render.Stack(children = children)

def screen(points, stale = False):
    if not points:
        return error_screen()
    latest = points[-1][1]
    change = percent_change(points[0][1], latest)
    change_color = "#66ff66" if change > 0 else "#ff5555" if change < 0 else "#dddddd"
    label = ("-" if change < 0 else "+") + fixed(change, 1) + "%"
    return render.Root(child = render.Column(cross_align = "center", children = [
        render.Padding(pad = (5, 0, 5, 0), child = render.Row(expanded = True, main_align = "space_between", children = [
            render.Text("USD>SEK" + ("*" if stale else ""), font = "tom-thumb", height = 6, color = "#ffffff"),
            render.Text("7D", font = "tom-thumb", height = 6, color = "#ffffff"),
        ])),
        render.Padding(pad = (5, 0, 5, 0), child = render.Row(expanded = True, main_align = "space_between", cross_align = "center", children = [
            render.Text(fixed(latest, 2), font = "6x10", height = 10, color = change_color),
            render.Text(label, font = "tom-thumb", height = 6, color = change_color),
        ])),
        chart(points, change_color),
    ]))

# Fixed currency pair; Pixlet still requires the config argument.
# buildifier: disable=unused-variable
def main(config):
    now = time.now().in_location("UTC")
    dates = [(now - time.parse_duration("%dh" % (24 * day))).format("2006-01-02") for day in range(PERIOD_DAYS - 1, -1, -1)]
    cached = json.decode(cache.get(CACHE_KEY) or "null", default = None)
    fallback = []
    if type(cached) == "dict":
        fallback = observations(cached.get("data"), dates)
        fetched = cached.get("fetched")
        if fallback and type(fetched) in ["int", "float"] and now.unix >= fetched and now.unix - fetched < REFRESH_SECONDS:
            return screen(fallback)

    # HTTP/data errors can fall back to cache. Pixlet cannot catch transport
    # failures (DNS/timeout/TLS) raised by http.get; those remain host-handled.
    response = http.get(URL, params = {
        "base": "USD",
        "quotes": "SEK",
        "providers": "ecb",
        "from": dates[0],
        "to": dates[-1],
    }, ttl_seconds = REFRESH_SECONDS)
    if response.status_code != 200:
        return screen(fallback, stale = True)
    data = json.decode(response.body(), default = None)
    points = observations(data, dates)
    if not points:
        return screen(fallback, stale = True)
    cache.set(CACHE_KEY, json.encode({"fetched": now.unix, "data": data}), ttl_seconds = 604800)
    return screen(points)
