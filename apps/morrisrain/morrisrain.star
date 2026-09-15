load("basemap.png", basemap_file = "file")
load("cache.star", "cache")
load("encoding/base64.star", "base64")
load("encoding/json.star", "json")
load("http.star", "http")
load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

WMS = "https://mesonet.agron.iastate.edu/cgi-bin/wms/hrrr/refd.cgi"
METADATA = "https://mesonet.agron.iastate.edu/data/gis/images/4326/hrrr/refd_%s.json"

# EPSG:3857; Morristown 40.7968 N, 74.4815 W. Approx. 175 miles E/W.
BBOX = "-8663268.36,4796402.90,-7919216.94,5168428.61"
BASEMAP = basemap_file.readall("rb")
CACHE_KEY = "morrisrain-175-v1"

def get_schema():
    return schema.Schema(version = "1", fields = [])

def placed(x, y, child):
    return render.Padding(pad = (x, y, 0, 0), child = child)

def error_screen(message):
    return render.Root(child = render.Box(width = 64, height = 32, child = render.Column(
        cross_align = "center",
        children = [render.Text("RAIN FCST", color = "#66ddff"), render.Text(message)],
    )))

def metadata(lead):
    response = http.get(METADATA % lead, ttl_seconds = 0)
    if response.status_code != 200:
        return None
    result = json.decode(response.body(), default = None)
    if type(result) != "dict" or type(result.get("model_init_utc")) != "string" or type(result.get("model_forecast_utc")) != "string":
        return None
    return result

def forecast_minutes(now_unix, init_unix):
    # First 15-minute forecast at or after now, followed by three hours.
    start = int((now_unix - init_unix + 899) // 900) * 15
    return range(start, start + 181, 30)

def frame(image_data, label):
    return render.Stack(children = [
        render.Image(src = BASEMAP),
        render.Image(src = image_data),
        # A 3px-wide/tall plus (five lit pixels), centered to pixel precision.
        placed(31, 16, render.Box(width = 3, height = 1, color = "#ffffff")),
        placed(32, 15, render.Box(width = 1, height = 3, color = "#ffffff")),
        render.Box(width = 20, height = 6, color = "#000000", child = render.Text("FCST", font = "tom-thumb", color = "#aaaaaa")),
        placed(43, 0, render.Box(width = 21, height = 6, color = "#000000", child = render.Text(label, font = "tom-thumb"))),
    ])

def animation(frames):
    return render.Root(delay = 1000, max_age = 1200, child = render.Animation(children = [
        frame(base64.decode(item["image"]), item["label"])
        for item in frames
    ]))

# Fixed Morristown map; config is required by Pixlet.
# buildifier: disable=unused-variable
def main(config):
    now = time.now().in_location("UTC")
    cached = json.decode(cache.get(CACHE_KEY) or "null", default = None)
    if type(cached) == "dict" and now.unix - cached.get("fetched", 0) < 600:
        return animation(cached["frames"])
    run = metadata("1080")
    if run == None:
        return error_screen("NO DATA")
    init = time.parse_time(run["model_init_utc"])
    age = now.unix - init.unix
    if age < 0 or age > 21600:
        return error_screen("OLD MODEL")
    frames = []
    for minute in forecast_minutes(now.unix, init.unix):
        lead = ("0000" + str(minute))[-4:]
        info = metadata(lead)
        if info == None or info["model_init_utc"] != run["model_init_utc"]:
            return error_screen("UPDATING")
        valid = time.parse_time(info["model_forecast_utc"])
        if int(valid.unix - init.unix) != minute * 60:
            return error_screen("BAD TIME")
        response = http.get(WMS, params = {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": "refd_" + lead,
            "STYLES": "",
            "SRS": "EPSG:3857",
            "BBOX": BBOX,
            "WIDTH": "64",
            "HEIGHT": "32",
            "FORMAT": "image/png",
            "TRANSPARENT": "TRUE",
        }, ttl_seconds = 0)
        if response.status_code != 200:
            return error_screen("MAP ERROR")
        image_data = response.body()
        if image_data[1:8] != "PNG\r\n\x1a\n":
            return error_screen("BAD IMAGE")
        frames.append({
            "image": base64.encode(image_data),
            "label": valid.in_location("America/New_York").format("15:04"),
        })

    # WMS follows the latest run. Reject a sequence crossing a model update.
    after = metadata("1080")
    if after == None or after["model_init_utc"] != run["model_init_utc"]:
        return error_screen("UPDATING")
    cache.set(CACHE_KEY, json.encode({"fetched": now.unix, "frames": frames}), ttl_seconds = 600)
    return animation(frames)
