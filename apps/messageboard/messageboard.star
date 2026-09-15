load("encoding/json.star", "json")
load("http.star", "http")
load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

COLORS = ["#ffffff", "#66ff66", "#ffdd66", "#ff88bb"]

def get_schema():
    return schema.Schema(version = "1", fields = [
        schema.Text(id = "server", name = "Message server", desc = "Pi address, e.g. http://192.168.0.127:8787 (use an IP if .local does not work).", icon = "link", default = ""),
    ])

def status(text):
    return render.Root(max_age = 60, child = render.Box(width = 64, height = 32, child = render.Text(text, font = "tb-8", color = "#888888")))

def wrap(text):
    lines = []
    line = ""
    for word in text.split():
        candidate = line + (" " if line else "") + word
        if render.Text(candidate, font = "tb-8").size()[0] <= 60:
            line = candidate
            continue
        if line:
            lines.append(line)
        line = ""
        for char in word.codepoints():
            if render.Text(line + char, font = "tb-8").size()[0] > 60:
                lines.append(line)
                line = ""
            line += char
    if line:
        lines.append(line)
    return lines

def message_screen(data):
    if type(data) != "dict" or type(data.get("text")) != "string":
        return status("NO SERVER")
    expires = data.get("expires_at")
    if expires != None and (type(expires) not in ["int", "float"] or expires <= time.now().unix):
        return []
    text = "".join(list(data["text"].codepoints())[:120]).strip()
    if not text:
        return []
    color = data.get("display_color")
    if color not in COLORS:
        color = "#ffffff"
    lines = wrap(text)
    pages = []
    total = (len(lines) + 2) // 3
    for index in range(total):
        children = [render.Padding(pad = (2, 3, 0, 0), child = render.Column(
            cross_align = "start",
            children = [render.Text(line, font = "tb-8", color = color) for line in lines[index * 3:index * 3 + 3]],
        ))]
        if total > 1:
            children.append(render.Padding(pad = (2, 31, 0, 0), child = render.Row(children = [
                render.Box(width = 60 // total, height = 1, color = color if page == index else "#222222")
                for page in range(total)
            ])))
        pages.append(render.Stack(children = children))
    max_age = 60 if expires == None else max(1, min(60, int(expires - time.now().unix)))
    return render.Root(max_age = max_age, delay = min(3000, 14000 // total), child = render.Animation(children = pages))

def main(config):
    server = (config.get("server") or "").strip().rstrip("/")
    if not server:
        return status("SET URL")
    if not server.startswith("http://") and not server.startswith("https://"):
        return status("BAD URL")
    response = http.get(server + "/api/message", ttl_seconds = 0)
    if response.status_code != 200:
        return status("NO SERVER")
    return message_screen(json.decode(response.body(), default = None))
