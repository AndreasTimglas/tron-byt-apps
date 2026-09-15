load("render.star", "render")
load("schema.star", "schema")

MESSAGE = "Anna, Anna, vad gör man en söndagmorgon"

def get_schema():
    return schema.Schema(version = "1", fields = [])

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

# Fixed message; config is required by Pixlet.
# buildifier: disable=unused-variable
def main(config):
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
        child = render.Text(MESSAGE, font = "tb-8", color = "#ffffff"),
    )))
    return render.Root(delay = 60, child = render.Stack(children = children))
