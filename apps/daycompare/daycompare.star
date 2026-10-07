load("encoding/json.star", "json")
load("math.star", "math")
load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

SWEDEN = '{"lat":"55.6050","lng":"13.0038","timezone":"Europe/Stockholm"}'
USA = '{"lat":"40.7968","lng":"-74.4815","timezone":"America/New_York"}'
RAD = math.pi / 180
PALETTES = [["#4488ff", "#ffdd33"], ["#ff5555", "#ffffff", "#4488ff"]]

def get_schema():
    return schema.Schema(version = "1", fields = [
        schema.Location(id = "sweden", name = "Swedish location", desc = "Blue/yellow curve. Defaults to Malmö.", icon = "locationDot"),
        schema.Location(id = "usa", name = "US location", desc = "Red/white/blue curve. Defaults to Morristown, NJ.", icon = "locationDot"),
    ])

def placed(x, y, child):
    return render.Padding(pad = (x, y, 0, 0), child = child)

def pixel(x, y, color):
    return placed(x, y, render.Box(width = 1, height = 1, color = color))

def coordinate(value, limit):
    if type(value) in ["int", "float"]:
        return value if value >= -limit and value <= limit else None
    if type(value) != "string" or not value:
        return None
    value = value.strip()
    digits = value[1:] if value.startswith("-") or value.startswith("+") else value
    if not digits or digits.count(".") > 1 or not digits.replace(".", "").isdigit():
        return None
    number = float(value)
    return number if number >= -limit and number <= limit else None

def location(value, default):
    data = json.decode(value or default, default = None)
    if type(data) != "dict":
        return None
    lat = coordinate(data.get("lat"), 90)
    lon = coordinate(data.get("lng"), 180)
    zone = data.get("timezone")
    if lat == None or lon == None or type(zone) != "string" or not zone:
        return None
    return (lat, lon, zone)

def solar(lat, lon, year, month, day, offset_hours):
    # NOAA fractional-year approximation, evaluated at local noon.
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    months = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    ordinal = day
    for days in months[:month - 1]:
        ordinal += days
    gamma = 2 * math.pi * (ordinal - 1) / (366 if leap else 365)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma) - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = 0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma) - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma) - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
    latitude = lat * RAD
    a = math.sin(latitude) * math.sin(decl)
    b = math.cos(latitude) * math.cos(decl)
    horizon = math.sin(-0.833 * RAD)
    if abs(b) < 0.0000001:
        length = 24.0 if a > horizon else 0.0
    else:
        crossing = (horizon - a) / b
        length = 24.0 if crossing <= -1 else 0.0 if crossing >= 1 else 2 * math.acos(crossing) / RAD / 15
    noon = (720 - eq - 4 * lon + 60 * offset_hours) / 60
    return {"length": length, "noon": noon, "rise": noon - length / 2, "set": noon + length / 2, "a": a, "b": b}

def axis(cities):
    # Polar conditions and daylight crossing midnight need the full clock axis.
    for city in cities:
        if city["length"] == 0 or city["length"] == 24 or city["rise"] < 0 or city["set"] > 24:
            return (0, 24)
    return (max(0, int(math.floor(min([c["rise"] for c in cities]) - 1))), min(24, int(math.ceil(max([c["set"] for c in cities]) + 1))))

def elevations(city, start, end):
    values = []
    for x in range(64):
        hour = start + x * (end - start) / 63.0
        angle = (hour - city["noon"]) * 15 * RAD
        values.append(math.asin(max(-1, min(1, city["a"] + city["b"] * math.cos(angle)))) / RAD)
    return values

def celebrate(sweden, usa):
    # Compare unrounded durations; tiny tolerance handles floating-point arithmetic.
    return abs(sweden["length"] - usa["length"]) * 60 <= 2 + 0.0000001

def fireworks(frame):
    children = []
    for cx, cy, delay, colors in [(15, 14, 0, ["#ffdd33", "#4488ff"]), (47, 14, 4, ["#ff5555", "#ffffff", "#4488ff"])]:
        age = frame - delay
        if age < 0 or age > 11:
            continue
        if age < 3:
            children.append(pixel(cx, 23 - age * 3, "#ffffff"))
        else:
            radius = 1 + (age - 3) // 2
            for i, direction in enumerate([(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]):
                x = cx + direction[0] * radius
                y = cy + direction[1] * radius
                if age < 9 or i % 2 == age % 2:
                    children.append(pixel(x, y, colors[i % len(colors)]))
    return children

def today(loc):
    local = time.now().in_location(loc[2])
    zone = local.format("-0700")
    offset = (int(zone[1:3]) + int(zone[3:5]) / 60.0) * (-1 if zone[0] == "-" else 1)
    return solar(loc[0], loc[1], int(local.format("2006")), int(local.format("01")), int(local.format("02")), offset)

def duration(hours):
    minutes = min(1440, max(0, int(hours * 60 + 0.5)))
    return str(minutes // 60) + ":" + ("0" if minutes % 60 < 10 else "") + str(minutes % 60)

def flag(us = False):
    children = []
    for y in range(5):
        for x in range(7):
            color = ("#4488ff" if x < 3 and y < 3 else "#ff5555" if y % 2 == 0 else "#ffffff") if us else ("#ffdd33" if x == 2 or y == 2 else "#4488ff")
            children.append(pixel(x, y, color))
    return render.Stack(children = children)

def curve(elevations, ceiling):
    points = {}
    for x, elevation in enumerate(elevations):
        if elevation < -0.833:
            continue
        y = 25 - int(max(0, elevation) * 15 / ceiling + 0.5)
        previous = elevations[x - 1] if x else elevation
        previous_y = 25 - int(max(0, previous) * 15 / ceiling + 0.5)
        for row in range(min(y, previous_y), max(y, previous_y) + 1):
            points[(x, row)] = True
    return points

def screen(sweden, usa):
    children = [
        render.Box(width = 64, height = 32, color = "#000000"),
        placed(0, 1, flag()),
        placed(57, 1, flag(True)),
    ]
    left = render.Text(duration(sweden["length"]), font = "tom-thumb", color = "#ffffff")
    right = render.Text(duration(usa["length"]), font = "tom-thumb", color = "#ffffff")
    children.extend([placed(9, 0, left), placed(55 - right.size()[0], 0, right)])

    start, end = axis([sweden, usa])
    samples = [elevations(city, start, end) for city in [sweden, usa]]

    # A common scale retains real differences in peak solar elevation.
    ceiling = max(10, min(90, (int(max(max(samples[0]), max(samples[1]))) // 10 + 1) * 10))
    for x in range(0, 64, 3):
        children.append(pixel(x, 25, "#333333"))
    curves = [curve(samples[0], ceiling), curve(samples[1], ceiling)]
    for index in range(2):
        for point in curves[index]:
            x, y = point
            if point in curves[1 - index] and x % 2 != index:
                continue
            palette = PALETTES[index]
            children.append(pixel(x, y, palette[(x // 3) % len(palette)]))

    # Four whole-hour labels placed at their actual time positions.
    hours = [start, start + (end - start) // 3, start + 2 * (end - start) // 3, end]
    for hour in hours:
        label = ("0" if hour < 10 else "") + str(hour)
        text = render.Text(label, font = "tom-thumb", height = 5, color = "#777777")
        x = int((hour - start) * 63.0 / (end - start) + 0.5)
        children.append(placed(max(0, min(64 - text.size()[0], x - text.size()[0] // 2)), 27, text))
    base = render.Stack(children = children)
    if not celebrate(sweden, usa):
        return render.Root(child = base)

    # A four-second loop, with clear pauses and no forced full-animation playback.
    frames = []
    for frame in range(20):
        frames.append(render.Stack(children = [base] + fireworks(frame - 2)))
    return render.Root(delay = 200, child = render.Animation(children = frames))

def main(config):
    sweden = location(config.get("sweden"), SWEDEN)
    usa = location(config.get("usa"), USA)
    if sweden == None or usa == None:
        return render.Root(child = render.Box(width = 64, height = 32, child = render.Text("SET CITY", font = "tb-8")))
    return screen(today(sweden), today(usa))
