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
        ), schema.Toggle(
            id = "details",
            name = "Show extra details",
            desc = "Use the denser layout with current humidity and feels-like temperature.",
            icon = "sliders",
            default = False,
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

def day_value(daily, key, day):
    values = daily.get(key)
    return values[day] if type(values) == "list" and len(values) > day else None

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

def small(text, color = "#ffffff", height = 5):
    return render.Text(text, font = "CG-pixel-3x5-mono", height = height, color = color)

def precipitation(value, compact = True):
    # A compact 3x5 droplet; six pixels total row height.
    pixels = [".b.", ".b.", "bbb", "bbb", ".b."]
    droplet = render.Column(children = [render.Row(children = [
        render.Box(width = 1, height = 1, color = "#66ddff" if pixel == "b" else "#000000")
        for pixel in line.elems()
    ]) for line in pixels])
    return render.Row(cross_align = "center", children = [
        droplet,
        render.Box(width = 1, height = 6),
        small(number(value, "%")) if compact else render.Text(number(value, "%"), font = "tb-8"),
    ])

def cell(width, height, child):
    return render.Box(width = width, height = height, child = child)

def simple_screen(current, daily):
    columns = []
    for day in range(2):
        condition = icon(current.get("weather_code") if day == 0 else day_value(daily, "weather_code", day))
        if day == 0:
            temperature = number(current.get("temperature_2m"), "°C")
            condition = render.Row(cross_align = "center", children = [
                condition,
                render.Box(width = 1, height = 1),
                render.Text(temperature, font = "tb-8" if len(temperature) <= 4 else "tom-thumb"),
            ])
        columns.append(render.Column(cross_align = "center", children = [
            cell(31, 6, render.Text("TODAY" if day == 0 else "TMRW", font = "tom-thumb", color = "#aaaaaa")),
            cell(31, 10, condition),
            cell(31, 8, render.Row(children = [
                render.Text(number(day_value(daily, "temperature_2m_max", day)), font = "tom-thumb", color = "#ff8866"),
                render.Text("/", font = "tom-thumb", color = "#666666"),
                render.Text(number(day_value(daily, "temperature_2m_min", day)), font = "tom-thumb", color = "#77aaff"),
            ])),
            cell(31, 8, precipitation(day_value(daily, "precipitation_probability_max", day), compact = False)),
        ]))
    return render.Root(max_age = 1800, child = render.Row(children = [
        columns[0],
        render.Box(width = 2, height = 32, color = "#181818"),
        columns[1],
    ]))

def weather_screen(data, details = False):
    if type(data) != "dict" or data.get("error"):
        return error_screen("API ERROR")
    current = data.get("current")
    daily = data.get("daily")
    if type(current) != "dict" or type(daily) != "dict" or current.get("temperature_2m") == None:
        return error_screen("NO DATA")
    if not details:
        return simple_screen(current, daily)
    temperature = number(current.get("temperature_2m"), "°C")

    # 42px today + 1px divider + 21px tomorrow. Every column totals 32px.
    today = render.Column(cross_align = "center", children = [
        cell(42, 5, small("TODAY", "#aaaaaa")),
        cell(42, 10, render.Row(cross_align = "center", children = [
            icon(current.get("weather_code")),
            render.Box(width = 2, height = 1),
            render.Text(temperature, font = "tb-8"),
        ])),
        cell(42, 6, render.Row(children = [
            small("H" + number(day_value(daily, "temperature_2m_max", 0)), "#ff8866"),
            render.Box(width = 3, height = 1),
            small("L" + number(day_value(daily, "temperature_2m_min", 0)), "#77aaff"),
        ])),
        cell(42, 5, render.Row(children = [
            small("F" + number(current.get("apparent_temperature")), "#ffcc66"),
            render.Box(width = 2, height = 1),
            small("H%" + number(current.get("relative_humidity_2m")), "#66ddff"),
        ])),
        cell(42, 6, precipitation(day_value(daily, "precipitation_probability_max", 0))),
    ])
    tomorrow = render.Column(cross_align = "center", children = [
        cell(21, 5, small("TMRW", "#aaaaaa")),
        cell(21, 10, icon(day_value(daily, "weather_code", 1))),
        cell(21, 6, small("H" + number(day_value(daily, "temperature_2m_max", 1)), "#ff8866")),
        cell(21, 5, small("L" + number(day_value(daily, "temperature_2m_min", 1)), "#77aaff")),
        cell(21, 6, precipitation(day_value(daily, "precipitation_probability_max", 1))),
    ])
    return render.Root(max_age = 1800, child = render.Row(children = [
        today,
        render.Box(width = 1, height = 32, color = "#333333"),
        tomorrow,
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
        "forecast_days": "2",
        "current": CURRENT,
        "daily": DAILY,
    }, ttl_seconds = 600)
    if response.status_code != 200:
        return error_screen("API ERROR")
    return weather_screen(json.decode(response.body(), default = None), details = config.bool("details"))
