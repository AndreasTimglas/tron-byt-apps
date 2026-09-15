load("encoding/json.star", "json")
load("http.star", "http")
load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

MESSAGE = "Anna, Anna, vad gör man en söndagmorgon"

def get_schema():
    return schema.Schema(version = "1", fields = [
        schema.Text(id = "server", name = "Message server", desc = "Pi URL, e.g. http://192.168.0.127:8787. Leave empty for the original Anna greeting.", default = "", icon = "link"),
    ])

def placed(x, y, child):
    return render.Padding(pad = (x, y, 0, 0), child = child)

def flower(color, upside_down = False):
    # Rounded upright blossom, two plump side petals, and a tiny green stem.
    # Intentionally suggestive botanical silhouettes, not anatomical drawings.
    pixels = ["..ppp..", ".ppppp.", ".ppppp.", "..ppp..", "ppppppp", "ppppppp", ".pp.pp.", "...g..."]
    if upside_down:
        pixels = pixels[::-1]
    return render.Column(children = [render.Row(children = [
        render.Box(width = 1, height = 1, color = color if pixel == "p" else "#449944" if pixel == "g" else "#000000")
        for pixel in row.elems()
    ]) for row in pixels])

def flower_screen(message, color = "#ffffff", max_age = 60):
    colors = ["#ff88aa", "#cc88ff", "#ffbb88", "#ff66aa"]
    children = [render.Box(width = 64, height = 32, color = "#000000")]
    for i in range(8):
        children.append(placed(i * 8, 0, flower(colors[i % 4])))
        children.append(placed(i * 8, 24, flower(colors[(i + 2) % 4], upside_down = True)))
    for y in [8, 16]:
        children.append(placed(0, y, flower("#cc88ff")))
        children.append(placed(57, y, flower("#ff88aa")))
    children.append(placed(9, 12, render.Marquee(
        width = 46,
        align = "center",
        child = render.Text(message, font = "tb-8", color = color),
    )))
    width = render.Text(message, font = "tb-8").size()[0]
    delay = min(60, 14000 // (width + 46))
    return render.Root(max_age = max_age, delay = delay, child = render.Stack(children = children))

def main(config):
    server = (config.get("server") or "").strip().rstrip("/")
    if not server:
        return flower_screen(MESSAGE)
    if not server.startswith("http://") and not server.startswith("https://"):
        return []
    response = http.get(server + "/api/flowers", ttl_seconds = 0)
    if response.status_code != 200:
        return []
    data = json.decode(response.body(), default = None)
    if type(data) != "dict" or type(data.get("text")) != "string":
        return []
    expires = data.get("expires_at")
    if type(expires) not in ["int", "float"] or expires <= time.now().unix:
        return []
    text = "".join(list(data["text"].codepoints())[:120]).strip()
    if not text:
        return []
    color = data.get("display_color")
    if color not in ["#ffffff", "#66ff66", "#ffdd66", "#ff88bb"]:
        color = "#ffffff"
    return flower_screen(text, color, max(1, min(60, int(expires - time.now().unix))))
