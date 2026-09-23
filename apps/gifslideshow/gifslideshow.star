load("encoding/base64.star", "base64")
load("encoding/json.star", "json")
load("http.star", "http")
load("render.star", "render")
load("schema.star", "schema")

def get_schema():
    return schema.Schema(version = "1", fields = [
        schema.Text(id = "server", name = "GIF server", desc = "Pi address, e.g. http://192.168.0.127:8787", default = "", icon = "link"),
    ])

def main(config):
    server = (config.get("server") or "").strip().rstrip("/")
    if not server or (not server.startswith("http://") and not server.startswith("https://")):
        return []
    response = http.get(server + "/api/gifs/next", ttl_seconds = 0)
    if response.status_code != 200:
        return []
    data = json.decode(response.body(), default = None)
    if type(data) != "dict" or type(data.get("frames")) != "list" or not data["frames"]:
        return []
    holds = data.get("holds", [1 for frame in data["frames"]])
    images = [render.Image(src = base64.decode(frame)) for frame in data["frames"]]
    frames = [image for index, image in enumerate(images) for repeat in range(holds[index])]
    return render.Root(delay = data.get("delay", 100), show_full_animation = True, child = render.Animation(children = frames))
