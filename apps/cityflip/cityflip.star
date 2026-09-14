load("encoding/json.star", "json")
load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

DEFAULT_LOCATION = '{"locality":"Malmö","description":"Malmö, Sweden","timezone":"Europe/Stockholm","lat":"55.6050","lng":"13.0038"}'

def get_schema():
    return schema.Schema(version = "1", fields = [
        schema.Location(id = "location", name = "Location", desc = "City and local timezone. Defaults to Malmö.", icon = "locationDot"),
        schema.Text(id = "city", name = "City label", desc = "Optional short name to display above the clock.", icon = "font", default = ""),
    ])

def placed(x, y, child):
    return render.Padding(pad = (x, y, 0, 0), child = child)

def card(digit):
    # One 13x24 split flap, using two subtle gray faces and a dark hinge.
    return render.Stack(children = [
        render.Box(width = 13, height = 24, color = "#171717"),
        render.Box(width = 13, height = 12, color = "#242424"),
        placed(2, 2, render.Text(digit, font = "10x20", height = 20, color = "#ffffff")),
        placed(0, 12, render.Box(width = 13, height = 1, color = "#080808")),
    ])

def clock_screen(city, hour, minute):
    digits = hour + minute
    colon = render.Stack(children = [
        render.Box(width = 5, height = 24),
        placed(2, 8, render.Box(width = 1, height = 1, color = "#aaaaaa")),
        placed(2, 16, render.Box(width = 1, height = 1, color = "#aaaaaa")),
    ])
    return render.Root(max_age = 90, child = render.Column(cross_align = "center", children = [
        render.Box(width = 64, height = 8, child = render.Text(city, font = "tb-8", color = "#bbbbbb")),
        render.Row(children = [
            card(digits[0]),
            render.Box(width = 1, height = 1),
            card(digits[1]),
            colon,
            card(digits[2]),
            render.Box(width = 1, height = 1),
            card(digits[3]),
        ]),
    ]))

def main(config):
    location = json.decode(config.get("location") or DEFAULT_LOCATION, default = None)
    if type(location) != "dict":
        return render.Root(child = render.Box(width = 64, height = 32, child = render.Text("SET CITY")))
    city = config.get("city") or location.get("locality") or location.get("description", "Local").split(",")[0]

    # Fit a small static label, keeping diacritics readable with tb-8.
    if len(city) > 10:
        city = city[:9] + "."
    local = time.now().in_location(location.get("timezone") or "Europe/Stockholm")
    return clock_screen(city, local.format("15"), local.format("04"))
