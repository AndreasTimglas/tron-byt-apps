"""Rebuild the static 64x32 map from Natural Earth and Terrarium DEM inputs.

Usage: python build_basemap.py land.geojson states.geojson terrain_dir output.png
terrain_dir must contain 6-18-23.png, 6-19-23.png, 6-18-24.png, 6-19-24.png.
Requires Pillow. No network access is performed by this script.
"""
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw

WEST, SOUTH, EAST, NORTH = -8663268.36, 4796402.90, -7919216.94, 5168428.61
R = 6378137


def project(point):
    lon, lat = point[:2]
    x = R * math.radians(lon)
    y = R * math.log(math.tan(math.pi / 4 + math.radians(max(-85, min(85, lat))) / 2))
    return ((x - WEST) / (EAST - WEST) * 64, (NORTH - y) / (NORTH - SOUTH) * 32)


def build(land_path, states_path, terrain_dir, output):
    mask = Image.new('1', (64, 32))
    draw = ImageDraw.Draw(mask)
    coasts = []
    for feature in json.loads(Path(land_path).read_text())['features']:
        geom = feature['geometry']
        polygons = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
        for polygon in polygons:
            for index, ring in enumerate(polygon):
                points = [project(p) for p in ring]
                draw.polygon(points, fill=1 if index == 0 else 0)
                coasts.append(points)
    tiles = {(x, y): Image.open(Path(terrain_dir) / f'6-{x}-{y}.png').convert('RGB')
             for x in (18, 19) for y in (23, 24)}
    image = Image.new('RGB', (64, 32), '#071d38')
    for py in range(32):
        for px in range(64):
            if not mask.getpixel((px, py)):
                continue
            mx = WEST + (px + 0.5) / 64 * (EAST - WEST)
            my = NORTH - (py + 0.5) / 32 * (NORTH - SOUTH)
            tx = (mx + math.pi * R) / (2 * math.pi * R) * 64
            ty = (math.pi * R - my) / (2 * math.pi * R) * 64
            red, green, blue = tiles[int(tx), int(ty)].getpixel((int(tx % 1 * 256), int(ty % 1 * 256)))
            elevation = red * 256 + green + blue / 256 - 32768
            # Muted green lowlands, olive foothills, brown highlands.
            color = '#14351d' if elevation < 200 else '#30381c' if elevation < 400 else '#493321' if elevation < 800 else '#61492f'
            image.putpixel((px, py), tuple(bytes.fromhex(color[1:])))
    draw = ImageDraw.Draw(image)
    for points in coasts:
        draw.line(points, fill='#304b4c', width=1)
    for feature in json.loads(Path(states_path).read_text())['features']:
        geom = feature['geometry']
        lines = geom['coordinates'] if geom['type'] == 'MultiLineString' else [geom['coordinates']]
        for line in lines:
            draw.line([project(p) for p in line], fill='#384337', width=1)
    image.save(output)


if __name__ == '__main__':
    build(*sys.argv[1:])
