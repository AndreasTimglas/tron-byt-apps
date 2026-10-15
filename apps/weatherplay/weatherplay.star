load("encoding/json.star", "json")
load("http.star", "http")
load("math.star", "math")
load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

FIELDS = ["temperature_2m", "weather_code", "wind_speed_10m", "wind_gusts_10m", "is_day"]
SNOW = [71, 73, 75, 77, 85, 86]
RAIN = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]
STORM = [95, 96, 99]
SCENES = ["sun", "cloud", "night", "fog", "wind", "fire", "rain", "snow", "storm"]
FRAMES = 48

DUCK = ["....yyy..", "....ykyoo", "y...yyy..", "yyyyyyy..", ".yyyyy..."]
SNOWMAN = [".........", ".........", "..wwww...", "..wkwwo..", "...ww....", ".wwwwww..", "wwwwkwww.", ".wwwwww.."]
UMBRELLA = ["...ppp...", ".ppppppp.", "ppppppppp", "...k.k...", "....k....", "....k....", "...kk...."]
CLOUD = ["....cccc....", "..cccccccc..", "cccccccccccc", ".cccccccccc."]
COLORS = {"y": "#ffdd35", "k": "#101526", "o": "#ff8730", "w": "#effaff", "p": "#ff559d", "c": "#9eafc9"}

def get_schema():
    return schema.Schema(version = "1", fields = [schema.Location(
        id = "location",
        name = "Location",
        desc = "Choose the location for your next-three-hour weather animation.",
        icon = "locationDot",
    )])

def at(x, y, child):
    return render.Padding(pad = (x, y, 0, 0), child = child)

def rect(items, x, y, w, h, color):
    # Clip every scene primitive below the header and inside the LED matrix.
    left = max(0, int(x))
    top = max(7, int(y))
    right = min(64, int(x) + w)
    bottom = min(32, int(y) + h)
    if right > left and bottom > top:
        items.append(at(left, top, render.Box(width = right - left, height = bottom - top, color = color)))

def sprite(items, x, y, rows):
    for dy, row in enumerate(rows):
        for dx, value in enumerate(row.elems()):
            if value != ".":
                rect(items, x + dx, y + dy, 1, 1, COLORS[value])

def wave(frame, period = 48):
    return math.sin(frame * 2 * math.pi / period)

def choose(rows):
    codes = [row["weather_code"] for row in rows]
    temp = max([row["temperature_2m"] for row in rows])
    windy = max([row["wind_speed_10m"] for row in rows]) >= 25 or max([row["wind_gusts_10m"] for row in rows]) >= 40
    scene = "sun"
    if any([code in STORM for code in codes]):
        scene = "storm"
    elif any([code in SNOW for code in codes]):
        scene = "snow"
    elif any([code in RAIN for code in codes]):
        scene = "rain"
    elif temp >= 30:
        scene = "fire"
    elif windy:
        scene = "wind"
    elif any([code in [45, 48] for code in codes]):
        scene = "fog"
    elif all([row["is_day"] == 0 for row in rows]):
        scene = "night"
    elif any([code in [2, 3] for code in codes]):
        scene = "cloud"
    return {"scene": scene, "temp": temp, "windy": windy}

def forecast(data, now):
    if type(data) != "dict" or type(data.get("hourly")) != "dict":
        return None
    hourly = data["hourly"]
    times = hourly.get("time")
    if type(times) != "list":
        return None
    for key in FIELDS:
        if type(hourly.get(key)) != "list" or len(hourly[key]) != len(times):
            return None
    rows = []
    for i, stamp in enumerate(times):
        # The next three hourly forecast points; Unix timestamps avoid DST ambiguity.
        if type(stamp) not in ["int", "float"] or stamp <= now or stamp > now + 10800:
            continue
        row = {}
        for key in FIELDS:
            value = hourly[key][i]
            if type(value) not in ["int", "float"] or value != value:
                return None
            row[key] = value
        if row["weather_code"] not in [0, 1, 2, 3, 45, 48] + RAIN + SNOW + STORM or row["is_day"] not in [0, 1] or abs(row["temperature_2m"]) > 100 or row["wind_speed_10m"] < 0 or row["wind_gusts_10m"] < 0:
            return None
        rows.append(row)
    return choose(rows) if len(rows) == 3 else None

def draw_fire(items, frame, temp, windy):
    strength = min(7, max(0, int(temp - 30)))
    for x in range(0, 64, 2):
        height = 7 + strength + int(3 * wave(frame * 2 + x * 3, 48) + 2 * wave(frame + x * 5, 24))
        lean = int(2 * wave(frame)) if windy else 0
        rect(items, x + lean, 32 - height, 2, height, "#d52b28")
        rect(items, x, 35 - height, 2, height, "#ff831e")
        rect(items, x, 39 - height, 2, height, "#ffe06a")
    for i in range(10):
        rect(items, (i * 13 + frame // 3) % 64, 30 - (frame + i * 7) % 23, 1, 1, "#ffb547")

def draw_rain(items, frame, storm, windy):
    for x in [-4, 8, 20, 32, 44, 56]:
        sprite(items, x + int(wave(frame) * 2), 8, CLOUD)
    for i in range(24 if storm else 16):
        y = 12 + (frame * 2 + i * 7) % 20
        x = (i * 17 + (frame if windy else 0)) % 64
        rect(items, x, y, 1, 2, "#61b8ff")
        if windy:
            rect(items, x + 1, y + 2, 1, 1, "#61b8ff")

    # Fill, then recede smoothly to loop without an abrupt reset.
    level = 27 - int(7 * (1 - math.cos(frame * 2 * math.pi / FRAMES)))
    rect(items, 0, level, 64, 32 - level, "#174bab")
    for x in range(64):
        y = level + int(wave(frame * 2 + x * 3, 48))
        rect(items, x, y, 1, 1, "#52d8ff")
    sprite(items, 27 + int(3 * wave(frame)), level - 4, DUCK)
    if storm and frame in [9, 10, 33]:
        for x, y in [(46, 12), (45, 13), (44, 14), (45, 15), (46, 15), (45, 16), (44, 17), (43, 18)]:
            rect(items, x, y, 2, 1, "#fff5ab")

def draw_snow(items, frame, windy):
    depth = 2 + int(2 * (1 - math.cos(frame * 2 * math.pi / FRAMES)))
    rect(items, 0, 32 - depth, 64, depth, "#c9e6f5")
    sprite(items, 28, 24 - depth, SNOWMAN)
    hat_x = 30
    hat_y = 24 - depth
    if frame >= 20 and frame < 40:
        hat_x += frame - 20
        hat_y -= (frame - 20) // 4
    rect(items, hat_x, hat_y, 4, 1, "#ff6666")
    rect(items, hat_x + 1, hat_y - 1, 2, 1, "#ff6666")
    for i in range(22):
        x = (i * 19 + int(3 * wave(frame + i * 3)) + (frame if windy else 0)) % 64
        y = 7 + (frame // 2 + i * 11) % 25
        rect(items, x, y, 1, 1, "#ffffff")
        if i % 6 == 0:
            rect(items, x - 1, y, 3, 1, "#ffffff")
            rect(items, x, y - 1, 1, 3, "#ffffff")

def draw_wind(items, frame):
    rect(items, 0, 30, 64, 2, "#285742")
    bend = 2 + int(2 * wave(frame))
    for y in range(18, 30):
        rect(items, 12 + (30 - y) * bend // 8, y, 2, 1, "#be8452")
    for x, y, w in [(9, 17, 11), (11, 14, 9), (13, 12, 5)]:
        rect(items, x + bend, y, w, 3, "#58ad63")
    for i in range(7):
        x = (frame * 2 + i * 13) % 76 - 6
        y = 10 + i * 3
        rect(items, x, y, 5, 1, "#587f91")
        rect(items, x + 5, y + 1, 2, 1, "#b9d85f")
    sprite(items, (frame * 2) % 80 - 10, 17 + int(3 * wave(frame)), UMBRELLA)

def draw_calm(items, frame, scene):
    rect(items, 0, 30, 64, 2, "#244d40")
    if scene == "night":
        for x, y in [(5, 12), (19, 9), (33, 15), (55, 12), (44, 23)]:
            rect(items, x, y, 1, 1, "#fff3b8" if frame % 16 < 8 else "#788dad")
        rect(items, 41, 9, 7, 8, "#ffe5a1")
        rect(items, 44, 8, 6, 6, "#071324")
    elif scene == "fog":
        rect(items, 45, 14, 1, 16, "#73869a")
        rect(items, 42, 13, 7, 1, "#b8c0bc")
        rect(items, 44, 14, 3, 2, "#ffda78")
        for i in range(5):
            rect(items, (frame + i * 17) % 85 - 20, 10 + i * 4, 30, 2, "#536578")
    else:
        rect(items, 10, 10, 9, 9, "#ffcb40")
        for x, y in [(13, 8), (13, 20), (7, 13), (20, 13)]:
            rect(items, x, y, 2, 2, "#ffe47b")
        rect(items, 10, 13, 9, 1, "#191f35")
        rect(items, 11, 14, 3, 2, "#191f35")
        rect(items, 16, 14, 3, 2, "#191f35")
        rect(items, 14, 17, 3, 1, "#9c5429")
        sprite(items, (frame // 2 + 30) % 78 - 12, 10, CLOUD)
        if scene == "cloud":
            sprite(items, 9 + frame // 4, 15, CLOUD)
            sprite(items, 39 - frame // 4, 18, CLOUD)
        rect(items, 47, 25, 1, 5, "#73bd5b")
        size = 1 if frame < 12 or frame >= 36 else 3
        rect(items, 46, 23, 3, 3, "#ff82ad")
        rect(items, 45, 24, 5, size, "#ff82ad")
        rect(items, 47, 24, 1, 1, "#ffe265")

def frame(state, tick):
    scene = state["scene"]
    items = [render.Box(width = 64, height = 32, color = "#071324")]
    if scene == "fire":
        draw_fire(items, tick, state["temp"], state["windy"])
    elif scene in ["rain", "storm"]:
        draw_rain(items, tick, scene == "storm", state["windy"])
    elif scene == "snow":
        draw_snow(items, tick, state["windy"])
    elif scene == "wind":
        draw_wind(items, tick)
    else:
        draw_calm(items, tick, scene)
    items.append(at(0, 0, render.Text("NEXT 3H", font = "tom-thumb", color = "#b5c6dc")))
    temp = state["temp"]
    label = render.Text(str(int(temp + 0.5 if temp >= 0 else temp - 0.5)) + "°C", font = "tom-thumb", color = "#ffffff")
    items.append(at(64 - label.size()[0], 0, label))
    return render.Stack(children = items)

def animate(state):
    return render.Root(delay = 150, max_age = 1800, child = render.Animation(children = [frame(state, i) for i in range(FRAMES)]))

def error_screen(message):
    return render.Root(child = render.Box(width = 64, height = 32, child = render.Column(cross_align = "center", children = [render.Text("WEATHER", color = "#ffbb66"), render.Text(message)])))

def coordinate(value, limit):
    if type(value) not in ["string", "int", "float"]:
        return None
    text = str(value).strip()
    digits = text[1:] if text.startswith("-") or text.startswith("+") else text
    if not digits or digits.count(".") > 1 or not digits.replace(".", "").isdigit():
        return None
    number = float(text)
    return number if -limit <= number and number <= limit else None

def main(config):
    raw = config.get("location")
    if not raw:
        return error_screen("SET CITY")
    loc = json.decode(raw, default = None)
    if type(loc) != "dict":
        return error_screen("BAD CITY")
    lat = coordinate(loc.get("lat"), 90)
    lon = coordinate(loc.get("lng"), 180)
    if lat == None or lon == None:
        return error_screen("BAD CITY")
    response = http.get("https://api.open-meteo.com/v1/forecast", params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "timezone": loc.get("timezone") or "auto",
        "hourly": ",".join(FIELDS),
        "timeformat": "unixtime",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "forecast_days": "2",
    }, ttl_seconds = 600)
    if response.status_code != 200:
        return error_screen("API ERROR")
    state = forecast(json.decode(response.body(), default = None), time.now().unix)
    return animate(state) if state != None else error_screen("NO DATA")
