load("encoding/json.star", "json")
load("http.star", "http")
load("render.star", "render")
load("schema.star", "schema")

URL = "https://api.open-meteo.com/v1/forecast"
CURRENT = "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code"
DAILY = "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"

def get_schema():
    return schema.Schema(
        version = "1",
        fields = [schema.Location(
            id = "location",
            name = "Location",
            desc = "Choose the location for your Celsius weather forecast.",
            icon = "locationDot",
        )],
    )

def error_screen(message):
    return render.Root(child = render.Box(width = 64, height = 32, child = render.Column(
        cross_align = "center",
        children = [render.Text("WEATHER", color = "#ff9955"), render.Text(message)],
    )))

def number(value, suffix = ""):
    if type(value) not in ["int", "float"] or value < -999 or value > 999:
        return "--" + suffix

    # Round halves away from zero, including negative temperatures.
    return str(int(value + 0.5 if value >= 0 else value - 0.5)) + suffix

def first(daily, key):
    values = daily.get(key)
    return values[0] if type(values) == "list" and values else None

def icon(code):
    # Original 9x9 pixel graphics. No external assets or emoji font needed.
    cloud = [".........", ".........", "...www...", "..wwwww..", ".wwwwwww.", "wwwwwwwww", ".wwwwwww."]
    if code in [0, 1]:
        pixels = ["....y....", ".y.....y.", "...yyy...", "..yyyyy..", "y.yyyyy.y", "..yyyyy..", "...yyy...", ".y.....y.", "....y...."]
    elif code == 2:
        pixels = [".y.......", "yyy......", ".y.www...", "..wwwww..", ".wwwwwww.", "wwwwwwwww", ".wwwwwww.", ".........", "........."]
    elif code == 3:
        pixels = cloud + [".........", "........."]
    elif code in [45, 48]:
        pixels = [".........", ".wwwwwww.", ".........", "wwwwwwwww", ".........", ".wwwwwww.", ".........", "wwwwwwwww", "........."]
    elif code in [71, 73, 75, 77, 85, 86]:
        pixels = cloud[:6] + [".........", ".w..w..w.", "........."]
    elif code in [95, 96, 99]:
        pixels = cloud[:6] + ["....yy...", "...yy....", "....y...."]
    elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        pixels = cloud[:6] + [".........", "..b..b..b", ".b..b..b."]
    else:
        return render.Text("?", color = "#aaaaaa")
    colors = {".": "#000000", "w": "#dddddd", "y": "#ffdd33", "b": "#4499ff"}
    return render.Column(children = [render.Row(children = [
        render.Box(width = 1, height = 1, color = colors[pixel])
        for pixel in line.elems()
    ]) for line in pixels])

def precipitation(value):
    # A 5x7 droplet with one pixel of spacing, fitting an 8-pixel row.
    pixels = ["..b..", "..b..", ".bbb.", ".bbb.", "bbbbb", "bbbbb", ".bbb."]
    droplet = render.Column(children = [render.Row(children = [
        render.Box(width = 1, height = 1, color = "#66ddff" if pixel == "b" else "#000000")
        for pixel in line.elems()
    ]) for line in pixels])
    return render.Row(cross_align = "center", children = [
        droplet,
        render.Box(width = 1, height = 8),
        render.Text(number(value, "%"), font = "tb-8"),
    ])

def reading(label, value, color):
    return render.Row(children = [
        render.Text(label, font = "tb-8", color = color),
        render.Text(value, font = "tb-8"),
    ])

def weather_screen(data):
    if type(data) != "dict" or data.get("error"):
        return error_screen("API ERROR")
    current = data.get("current")
    daily = data.get("daily")
    if type(current) != "dict" or type(daily) != "dict" or current.get("temperature_2m") == None:
        return error_screen("NO DATA")
    temperature = number(current.get("temperature_2m"), "°C")
    return render.Root(max_age = 1800, child = render.Row(children = [
        render.Box(width = 32, height = 32, child = render.Column(
            cross_align = "center",
            children = [
                render.Text(temperature, font = "6x13" if len(temperature) <= 5 else "tb-8", height = 13),
                render.Box(width = 32, height = 11, child = icon(current.get("weather_code"))),
                render.Text("H%" + number(current.get("relative_humidity_2m")), font = "tb-8", color = "#66ddff"),
            ],
        )),
        render.Box(width = 1, height = 32, color = "#333333"),
        render.Box(width = 31, height = 32, child = render.Column(
            cross_align = "start",
            children = [
                reading("F", number(current.get("apparent_temperature"), "°"), "#ffcc66"),
                reading("H", number(first(daily, "temperature_2m_max"), "°"), "#ff8866"),
                reading("L", number(first(daily, "temperature_2m_min"), "°"), "#77aaff"),
                precipitation(first(daily, "precipitation_probability_max")),
            ],
        )),
    ]))

def main(config):
    raw_location = config.get("location")
    if not raw_location:
        return error_screen("SET LOCATION")
    location = json.decode(raw_location, default = None)
    if type(location) != "dict" or location.get("lat") == None or location.get("lng") == None:
        return error_screen("BAD LOCATION")

    # Pixlet has no try/except or catch builtin. Transport failures propagate
    # to the host; HTTP errors and malformed response bodies are handled here.
    response = http.get(URL, params = {
        "latitude": location["lat"],
        "longitude": location["lng"],
        "timezone": location.get("timezone") or "auto",
        "temperature_unit": "celsius",
        "forecast_days": "1",
        "current": CURRENT,
        "daily": DAILY,
    }, ttl_seconds = 600)
    if response.status_code != 200:
        return error_screen("API ERROR")
    return weather_screen(json.decode(response.body(), default = None))
