"""Print the Sunday edition using an offline, three-times oversampled ink plate."""

from functools import lru_cache
import json
import math
import os
from pathlib import Path
from random import Random
import struct
import zlib

from illustrations import SCENES, Scene


ROOT = Path(__file__).resolve().parent
SIDE = 1024
SCALE = 3
WIDTH = SIDE * SCALE
PAPER = (246, 236, 213)
# Astryx Stone Light palette stops used as print inks.
SWATCHES = {
    "neutral": ("25252a", "46464e", "919197", "f0f0f7"),
    "red": ("381d19", "603c37", "d8ada6", "ffece9"),
    "blue": ("17263a", "344861", "a4bbda", "e8f2ff"),
    "teal": ("112b24", "2c4f44", "a1c1b6", "e6f5ef"),
    "purple": ("2a2135", "4c405b", "beb2d2", "f4edff"),
    "orange": ("36200d", "5e3f27", "d7b18d", "ffeddd"),
    "cyan": ("0c2a31", "264d57", "99c1cb", "def6fc"),
}

# Additional halftone inks appear in the illustrations and newsprint.
ART_INKS = {
    "paper": "f8efd9", "rule": "c5b68f", "faint": "e7dac0",
    "warm": "70554a", "wear1": "463731", "wear2": "3f2e31", "wear3": "584138",
    "night": "182335", "night2": "2c3b50", "slate": "596c7b",
    "steel": "899da6", "sky": "bacccd", "mist": "d4dcd1",
    "sun": "e4ba61", "sand": "ccae7a", "umber": "8e6e55",
    "rust": "a04d38", "flame": "d77846", "brick": "743c35",
    "ocean": "416e78", "pine": "3c6559", "leaf": "729179",
    "grass": "a8aa74", "cream": "eee5c9", "white": "fbf7ed",
}
ink_values = dict(ART_INKS)
for hue, colors in SWATCHES.items():
    for stop, value in zip((15, 30, 75, 95), colors, strict=True):
        ink_values[f"{hue}{stop}"] = value
PALETTE = {name: index for index, name in enumerate(ink_values, 1)}
INK = (None, *(tuple(bytes.fromhex(value)) for value in ink_values.values()))
BLACK = PALETTE["neutral15"]
RED = PALETTE["red30"]
MUTED = PALETTE["blue30"]
RULE = PALETTE["rule"]
FAINT = PALETTE["faint"]
WHITE = PALETTE["white"]


class Press:
    def __init__(self):
        self.plate = bytearray(WIDTH * WIDTH)
        self.fonts = json.loads(zlib.decompress((ROOT / "materials/glyphs.json.z").read_bytes()))

    @lru_cache(maxsize=4096)
    def stencil(self, face, character, horizontal, vertical):
        _, bearing, top, width, height, mask = self.fonts[face][character]
        bits = bytes.fromhex(mask)
        stride = (width + 7) // 8
        points = []
        for row in range(round(height * vertical)):
            src_y = min(height - 1, int(row / vertical)) * stride
            for col in range(round(width * horizontal)):
                src_x = min(width - 1, int(col / horizontal))
                if bits[src_y + src_x // 8] & (128 >> (src_x % 8)):
                    points.append((round(bearing * horizontal) + col, round(top * vertical) + row))
        return points

    def text(self, value, face, x, y, size=1, stretch=1, align=0, ink=BLACK, wear=False, limit=None):
        units = self.fonts[face]
        step = [round(units[c][0] * size * stretch) for c in value]
        length = sum(step) / SCALE
        if limit is not None and length > limit:
            if limit / length < .73:
                raise ValueError(f"Text exceeds column by {length - limit:.1f}px: {value}")
            return self.text(value, face, x, y, size, stretch * (limit - 1) / length, align, ink, wear)
        cursor = round((x - align * length) * SCALE)
        baseline = round(y * SCALE)
        for index, (char, advance) in enumerate(zip(value, step, strict=True)):
            seed = (2654435761 * (20261122 + cursor + baseline * 1031 + index * 29)) & 0xffffffff
            tint = PALETTE[f"wear{1 + (seed >> 8) % 3}"] if wear else ink
            for dx, dy in self.stencil(face, char, size * stretch, size):
                xx, yy = cursor + dx, baseline + dy
                if 0 <= xx < WIDTH and 0 <= yy < WIDTH:
                    if wear and (seed + xx // 2 * 13 + yy // 2 * 7) % 113 < 4:
                        continue
                    self.plate[yy * WIDTH + xx] = tint
                    if wear and yy + 2 < WIDTH and (seed + xx * 7 + yy) % 31 < 3:
                        spot = (yy + 2) * WIDTH + xx
                        if not self.plate[spot]:
                            self.plate[spot] = RULE
            cursor += advance
        return length

    def box(self, x, y, w, h, ink):
        left, top, right, bottom = (round(v * SCALE) for v in (x, y, x + w, y + h))
        if min(left, top) < 0 or max(right, bottom) > WIDTH:
            raise ValueError(f"Box outside plate: {(x, y, w, h)}")
        fill = bytes((ink,)) * (right - left)
        for row in range(top, bottom):
            self.plate[row * WIDTH + left:row * WIDTH + right] = fill

    def path(self, points, ink=BLACK, weight=1):
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            steps = max(1, round(max(abs(bx - ax), abs(by - ay)) * SCALE))
            for i in range(steps + 1):
                x = ax + (bx - ax) * i / steps
                y = ay + (by - ay) * i / steps
                self.box(x - weight / 2, y - weight / 2, weight, weight, ink)

    def ellipse(self, x, y, rx, ry, ink=BLACK, weight=1):
        points = [(x + rx * math.cos(i * math.pi / 48), y + ry * math.sin(i * math.pi / 48))
                  for i in range(97)]
        self.path(points, ink, weight)

    def rule(self, x, y, width, ink=BLACK, weight=1):
        self.box(x, y, width, weight, ink)

    def frame(self, x, y, w, h, ink=RULE):
        self.path(((x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)), ink, .8)


COASTS = (
    ((-166,64),(-146,60),(-129,54),(-124,46),(-117,32),(-101,20),(-88,18),(-83,10),
     (-77,8),(-81,21),(-90,28),(-82,30),(-76,37),(-65,46),(-57,52),(-67,58),(-59,64),
     (-81,72),(-110,72),(-134,68),(-155,71),(-166,64)),
    ((-81,10),(-67,10),(-57,5),(-34,-7),(-39,-20),(-51,-32),(-61,-54),(-69,-54),
     (-75,-41),(-71,-24),(-78,-11),(-81,10)),
    ((-54,61),(-44,60),(-23,67),(-20,78),(-36,83),(-61,78),(-54,61)),
    ((-11,36),(-9,44),(1,50),(9,54),(17,59),(25,71),(46,69),(62,72),(82,73),
     (111,73),(134,69),(159,63),(177,65),(166,55),(146,49),(142,36),(124,35),
     (120,22),(109,18),(104,2),(96,7),(90,23),(79,10),(71,19),(66,26),(56,26),
     (48,30),(36,35),(31,41),(22,39),(16,39),(9,44),(3,43),(-2,36),(-11,36)),
    ((-17,13),(-17,26),(-6,35),(12,36),(26,32),(33,30),(43,12),(51,11),(47,1),
     (40,-11),(34,-19),(25,-34),(18,-34),(12,-19),(11,-7),(5,5),(-7,5),(-17,13)),
    ((95,5),(105,1),(109,-6),(121,-9),(132,-8)), ((114,5),(118,-3),(124,1)),
    ((112,-22),(123,-14),(135,-13),(145,-12),(154,-27),(151,-36),(141,-39),
     (131,-31),(115,-34),(112,-22)),
    ((132,34),(137,36),(141,42),(143,45)), ((166,-45),(172,-42),(178,-36)),
)


LEFT = 30
RIGHT = 994
PAGE = RIGHT - LEFT


def number_tag(p, number, x, y, ink, width=19):
    p.box(x, y, width, 13, ink)
    p.text(f"{number:02d}", "news12", x+width/2, y+10, .85, align=.5, ink=WHITE)


def measure(p, value, face, size):
    units = p.fonts[face]
    return sum(round(units[char][0]*size) for char in value) / SCALE


def headline(p, lines, x, y, width, size, line_height, face):
    longest = max(measure(p, line, face, size) for line in lines)
    stretch = min(1, (width-1)/longest)
    for index, line in enumerate(lines):
        p.text(line, face, x, y + index*line_height, size, stretch=stretch)


def masthead(p, edition, counts, colors):
    p.rule(LEFT, 20, PAGE, BLACK, 2)
    p.text("THE WORLD DISPATCH", "display22", LEFT, 43, 1, ink=RED)
    p.text(f"SUNDAY EDITION   /   {sum(counts.values())} STORIES   /   {len(counts)} REGIONS",
           "news12", RIGHT, 42, .97, align=1, ink=MUTED)
    p.rule(LEFT, 49, PAGE, RULE, .85)
    p.text("22 NOVEMBER 2026", "display55", 512, 111, 1.39, 1.0, .5, wear=True, limit=PAGE)
    p.text(edition["summary"], "news14", 512, 135, 1.16, align=.5, limit=PAGE)
    p.rule(LEFT, 145, PAGE, BLACK, 1.35)

    width = PAGE / len(edition["numbers"])
    for i, (value, label, story) in enumerate(edition["numbers"]):
        x = LEFT + i*width
        if i:
            p.box(x, 153, .7, 40, RULE)
        p.text(value, "display27", x+width/2, 174, 1.07, align=.5, ink=RED, limit=width-8)
        p.text(f"{story}  /  {label}", "news12", x+width/2, 189, .91, align=.5,
               ink=MUTED, limit=width-9)

    width = PAGE / len(colors)
    for i, (region, color) in enumerate(colors.items()):
        x = LEFT+i*width
        p.box(x, 201, width, 20, color)
        p.text(f"{region}  {counts[region]}", "news12", x+width/2, 215, 1.02, align=.5, ink=WHITE)

    p.box(LEFT, 226, PAGE, 19, PALETTE["paper"])
    p.rule(LEFT, 226, PAGE, RULE, .8)
    p.rule(LEFT, 244, PAGE, RULE, .8)
    p.text("UTC", "news12", LEFT+8, 239.3, 1.06, ink=RED)
    step = (PAGE-49) / len(edition["timeline"])
    for i, (hour, title, story) in enumerate(edition["timeline"]):
        x = LEFT + 49 + i*step
        p.box(x-4, 230, .6, 10, RULE)
        p.text(hour, "news12", x+1, 239, .91, ink=RED)
        p.text(title, "news12", x+38, 239, .85, ink=BLACK, limit=step-43)


def leading_stories(p, edition, colors):
    for index, (row, (x,w)) in enumerate(zip(edition["leads"],
                                            ((30,402),(448,265),(729,265)), strict=True), 1):
        stop = colors[row["region"]]
        p.rule(x, 254, w, stop, 2)
        SCENES[row["scene"]](Scene(p, PALETTE, x, 256, w, 102))
        number_tag(p, index, x, 256, stop, width=24)
        if index == 3:
            for start, label in ((x+6, "IRAN'S CLAIM"), (x+w/2+5, "BAHRAIN'S ACCOUNT")):
                p.box(start, 341, 103, 13, PALETTE["paper"])
                p.text(label, "news12", start+5, 350.5, .78, ink=RED)
        p.text(row["place"], "news12", x, 375, 1.03, ink=stop)
        p.text(row["tag"], "news12", x+w, 375, .89, align=1, ink=stop)
        headline(p, row["headline"], x, 405 if index == 1 else 406, w,
                 .70 if index == 1 else 1.05, 33 if index == 1 else 26,
                 "display55" if index == 1 else "display27")
        for line, detail in enumerate(row["detail"]):
            p.text(detail, "news14", x, 459+line*15, 1.02, limit=w)
        p.text(row["source"], "news12", x, 489, .91, ink=MUTED, limit=w)
        if index < 3:
            p.box(x+w+7, 254, .8, 235, RULE)


def illustrated_desk(p, edition, colors):
    p.rule(LEFT, 499, PAGE, BLACK, 1.3)
    p.text("Around the World", "display22", LEFT, 520, .98)
    p.text("ILLUSTRATED REPORTS 04-15", "news12", RIGHT, 519, .92, align=1, ink=MUTED)
    width = (PAGE-5*10)/6
    for index, (region, place, tag, title, detail, source, scene, loc) in enumerate(edition["cards"]):
        row, col = divmod(index, 6)
        x, y = LEFT+col*(width+10), 529+row*103
        color = colors[region]
        p.rule(x, y, width, color, 2)
        SCENES[scene](Scene(p, PALETTE, x, y+2, width, 36))
        number_tag(p, index+4, x, y+2, color)
        p.text(place, "news12", x, y+49, .86, ink=color)
        headline(p, title, x, y+64, width, .73, 14, "display22")
        p.text(detail, "news12", x, y+89, .86, limit=width)
        p.text(f"{tag}  /  {source}", "news12", x, y+99, .75, ink=MUTED, limit=width)


def point_in_coast(lon, lat, coast):
    if len(coast) < 4 or coast[0] != coast[-1]:
        return False
    return sum(
        min(lat1, lat2) <= lat < max(lat1, lat2)
        and lon < lon1 + (lon2-lon1)*(lat-lat1)/(lat2-lat1)
        for (lon1, lat1), (lon2, lat2) in zip(coast, coast[1:])
    ) % 2


def world_map(p, edition, colors):
    x, y, w, h = LEFT, 741, 313, 179
    p.box(x, y, w, h, PALETTE["night"])
    p.text("WORLD MAP", "display22", x+9, y+20, .85, ink=WHITE)
    p.text("PINS MATCH STORY NUMBERS", "news12", x+w-9, y+19, .77, ink=PALETTE["sky"], align=1)
    p.rule(x+9, y+25, w-18, PALETTE["slate"], .7)

    def project(lon, lat):
        return x+13+(lon+180)*(w-26)/360, y+33+(84-lat)*.91

    for lat in range(-56, 84, 4):
        for lon in range(-176, 180, 4):
            if any(point_in_coast(lon, lat, coast) for coast in COASTS):
                px, py = project(lon, lat)
                p.box(px-.78, py-.72, 1.56, 1.44, PALETTE["blue75"])
    for lon, lat in ((106,-7),(115,-8),(120,-9),(124,-4),(136,35),(140,39),(144,44),
                     (171,-43),(175,-39),(178,-37),(48,-19)):
        px, py = project(lon, lat)
        p.box(px-.85, py-.85, 1.7, 1.7, PALETTE["blue75"])

    sites = [(row["region"], row["map"]) for row in edition["leads"]]
    sites.extend((row[0],row[-1]) for row in edition["cards"])
    pins = []
    for number, (region, location) in enumerate(sites, 1):
        if location is None:
            continue
        lon,lat,dx,dy = location
        px,py = project(lon,lat)
        p.path(((px,py),(px+dx,py+dy)), PALETTE["sky"], .7)
        p.box(px-1,py-1,2,2,WHITE)
        pins.append((number,px+dx,py+dy,colors[region]))
    for number, px, py, color in pins:
        p.box(px-8.5,py-6.5,17,13,PALETTE["cream"])
        p.box(px-7.5,py-5.5,15,11,color)
        p.text(f"{number:02d}", "news12", px, py+3.1, .74, align=.5, ink=WHITE)
    p.text("SELECTED LOCATIONS  /  NOT TO SCALE", "news12", x+9, y+h-7, .78, ink=PALETTE["sky"])


def briefs(p, edition, colors):
    x = 357
    p.rule(x, 741, RIGHT-x, BLACK, 1)
    p.text("Also on Sunday", "display22", x, 760, .94)
    p.text("REPORTS 16-37   /   STATUS & SOURCE AT RIGHT", "news12", RIGHT, 759, .86,
           align=1, ink=MUTED)
    for i, (region, tag, title, source) in enumerate(edition["briefs"]):
        col, row = divmod(i, 11)
        left = x+col*322
        y = 775+row*14.1
        p.box(left, y-7.5, 2.4, 8, colors[region])
        p.text(f"{i+16:02d}", "news12", left+6, y, .87, ink=colors[region])
        meta = f"{tag} / {source}"
        meta_w = measure(p, meta, "news12", .65)
        p.text(title, "news12", left+24, y, .91, limit=282-meta_w)
        p.text(meta, "news12", left+314, y, .65, align=1, ink=MUTED)
        p.rule(left, y+3.8, 314, FAINT, .52)


def footer(p, edition):
    p.box(LEFT, 928, PAGE, 38, PALETTE["paper"])
    p.frame(LEFT, 928, PAGE, 38, RED)
    p.text("DATE CHECK", "display22", LEFT+10, 950, .75, ink=RED)
    p.box(LEFT+130, 935, .7, 23, RULE)
    for i, line in enumerate(edition["date_check"]):
        p.text(line, "news12", LEFT+141, 943+i*13, .90, limit=PAGE-152)
    p.rule(LEFT, 975, PAGE, BLACK, 1.25)
    p.text("MARKETS", "display22", LEFT, 991, .70, ink=MUTED)
    p.text("FRI 20 NOV", "news12", LEFT, 1004, .84, ink=MUTED)
    for i, (label,value) in enumerate(edition["markets"]):
        x = LEFT+116+i*130
        p.box(x, 981, .7, 25, RULE)
        p.text(label, "news12", x+9, 990, .82, ink=MUTED)
        p.text(value, "display22", x+9, 1006, .69, ink=RED)
    p.text("ORIGINAL SCENE ILLUSTRATIONS", "news12", RIGHT, 991, .82, align=1, ink=MUTED)
    p.text("DATES CHECKED IN LOCAL TIME AND UTC", "news12", RIGHT, 1004, .82, align=1, ink=MUTED)


def compose(edition):
    if tuple(len(edition[k]) for k in ("leads", "cards", "briefs")) != (3, 12, 22):
        raise ValueError("Unexpected number of lead stories, cards or briefs")
    colors = {region: PALETTE[hue+"30"] for region,hue in edition["regions"]}
    counts = dict.fromkeys(colors, 0)
    for region in [row["region"] for row in edition["leads"]] + [
            row[0] for row in edition["cards"]+edition["briefs"]]:
        counts[region] += 1
    p = Press()
    masthead(p, edition, counts, colors)
    leading_stories(p, edition, colors)
    illustrated_desk(p, edition, colors)
    world_map(p, edition, colors)
    briefs(p, edition, colors)
    footer(p, edition)
    return p.plate


def paper_tone(random, x, y):
    edge = min(x, y, SIDE-1-x, SIDE-1-y)
    fold = 2 if 505 <= x <= 510 else 0
    stain = round(2*math.cos(x/174 + y/246) + 2*math.sin(y/83) - 2*math.cos((x-y)/215))
    aging = max(0, 26-edge) * (3 + ((x*19 + y*31) % 5)) // 14
    if edge < 15 and (x + y*3) % 13 == 0:
        aging += 4
    grain = random.randrange(4) - 2
    return min(11, max(-40, grain + stain - aging - fold))


def raster_rows(plate):
    random = Random(20261122)
    stock = {tone: bytes(min(255, max(0, c+tone)) for c in PAPER) for tone in range(-40,12)}
    palette = {}
    blank = bytes(SCALE * SCALE)
    for y in range(SIDE):
        rows = [plate[(y*SCALE+j)*WIDTH:(y*SCALE+j+1)*WIDTH] for j in range(SCALE)]
        out = bytearray()
        for x in range(SIDE):
            i = x*SCALE
            tone = paper_tone(random, x, y)
            ground = stock[tone]
            flecks = rows[0][i:i+SCALE] + rows[1][i:i+SCALE] + rows[2][i:i+SCALE]
            if flecks == blank:
                out.extend(ground)
                continue
            ranked = bytes(sorted(flecks))
            key = (tone, ranked)
            color = palette.get(key)
            if color is None:
                samples = [INK[index] for index in ranked if index]
                color = bytes((sum(ink[c] for ink in samples) + (9-len(samples))*ground[c]+4)//9
                              for c in range(3))
                palette[key] = color
            out.extend(color)
        yield out


def png_chunk(kind, data):
    return struct.pack(">I",len(data)) + kind + data + struct.pack(">I",zlib.crc32(kind+data))


def write_image(path, plate):
    compressor = zlib.compressobj(level=9)
    blocks = []
    for row in raster_rows(plate):
        horizontal = bytearray((1,)) + row[:3]
        horizontal.extend((right-left) % 256 for left, right in zip(row, row[3:]))
        blocks.append(compressor.compress(horizontal))
    blocks.append(compressor.flush())
    payload = b"".join(blocks)
    info = struct.pack(">IIBBBBB", SIDE, SIDE, 8, 2, 0, 0, 0)
    image = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR",info) + png_chunk(b"IDAT",payload) + png_chunk(b"IEND",b"")
    if len(image) > 1048576:
        raise ValueError(f"Edition exceeds 1 MiB: {len(image)} bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image)


if __name__ == "__main__":
    edition = json.loads((ROOT / "edition.json").read_text(encoding="utf-8"))
    output = Path(os.getenv("MAKEFUN_OUTPUT_DIR", "/output")) / "entry.png"
    write_image(output, compose(edition))
