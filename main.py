"""Print the Sunday edition using an offline, three-times oversampled ink plate."""

from functools import lru_cache
import json
import math
import os
from pathlib import Path
from random import Random
import struct
import zlib


ROOT = Path(__file__).resolve().parent
SIDE = 1024
SCALE = 3
WIDTH = SIDE * SCALE
PAPER = (246, 236, 213)
INK = (
    (0, 0, 0), (37, 37, 42), (88, 65, 62), (60, 72, 86),
    (122, 108, 89), (203, 187, 153), (230, 217, 188),
    (70, 55, 49), (63, 46, 49), (88, 65, 56),
)
CLIMATE, WORLD, CIVIC, SCIENCE, CULTURE = 2, 3, 3, 4, 4
SECTION = {
    "Climate": CLIMATE, "World": WORLD, "Civic": CIVIC,
    "Science": SCIENCE, "Culture": CULTURE,
}


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

    def text(self, value, face, x, y, size=1, stretch=1, align=0, ink=1, wear=False, limit=None):
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
            tint = 7 + (seed >> 8) % 3 if wear and ink == 1 else ink
            for dx, dy in self.stencil(face, char, size * stretch, size):
                xx, yy = cursor + dx, baseline + dy
                if 0 <= xx < WIDTH and 0 <= yy < WIDTH:
                    if wear and (seed + xx // 2 * 13 + yy // 2 * 7) % 113 < 4:
                        continue
                    self.plate[yy * WIDTH + xx] = tint
                    if wear and yy + 2 < WIDTH and (seed + xx * 7 + yy) % 31 < 3:
                        spot = (yy + 2) * WIDTH + xx
                        if not self.plate[spot]:
                            self.plate[spot] = 5
            cursor += advance
        return length

    def box(self, x, y, w, h, ink):
        left, top, right, bottom = (round(v * SCALE) for v in (x, y, x + w, y + h))
        if min(left, top) < 0 or max(right, bottom) > WIDTH:
            raise ValueError(f"Box outside plate: {(x, y, w, h)}")
        fill = bytes((ink,)) * (right - left)
        for row in range(top, bottom):
            self.plate[row * WIDTH + left:row * WIDTH + right] = fill

    def path(self, points, ink=1, weight=1):
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            steps = max(1, round(max(abs(bx - ax), abs(by - ay)) * SCALE))
            for i in range(steps + 1):
                x = ax + (bx - ax) * i / steps
                y = ay + (by - ay) * i / steps
                self.box(x - weight / 2, y - weight / 2, weight, weight, ink)

    def ellipse(self, x, y, rx, ry, ink=1, weight=1):
        points = [(x + rx * math.cos(i * math.pi / 48), y + ry * math.sin(i * math.pi / 48))
                  for i in range(97)]
        self.path(points, ink, weight)

    def rule(self, x, y, width, ink=1, weight=1):
        self.box(x, y, width, weight, ink)

    def frame(self, x, y, w, h, ink=5):
        self.path(((x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)), ink, .8)


def chart_ground(p, x, y, w, h):
    p.frame(x, y, w, h)
    for gy in range(y + 7, y + h - 1, 9):
        for gx in range(x + 7, x + w - 1, 8):
            p.box(gx, gy, .65, .65, 5)


def climate_plate(p, x, y, w, h):
    chart_ground(p, x, y, w, h)
    gx, gy = x + 75, y + 64
    p.ellipse(gx, gy, 49, 48, 3, 1.5)
    p.ellipse(gx, gy, 25, 48, 3)
    p.ellipse(gx, gy, 49, 17, 3)
    p.path(((gx,gy-48),(gx,gy+48)), 3)
    p.path(((gx-48,gy),(gx+48,gy)), 3)
    p.box(gx+72, y+16, w-166, h-32, 6)
    right = x + w - 19
    left = gx + 83
    p.frame(left, y+21, right-left, h-42, 4)
    p.text("DRAFT AGREEMENT", "news12", left+9, y+41, 1.03, ink=4, limit=right-left-18)
    for line in (49, 56, 91, 98):
        p.rule(left+9, y+line, right-left-18, 5, .8)
    p.text("FOSSIL FUELS", "display22", left+9, y+78, .88, ink=2, limit=right-left-18)
    p.path(((left+6,y+69),(right-10,y+69)), 2, 1.5)
    for i in range(5):
        p.path(((gx-47+i*8,gy+51),(gx-32+i*8,gy+56)), 3, .8)


def ship_plate(p, x, y, w, h):
    chart_ground(p, x, y, w, h)
    sx, sy = x + 17, y + 86
    hull = ((0,0),(w-34,0),(w-61,23),(25,23),(0,0))
    p.path([(sx+a,sy+b) for a,b in hull], 3, 2)
    for i in range(18, w-56, 7):
        p.path(((sx+i,sy+3),(sx+i+13,sy+17)), 3, .8)
    p.path(((sx+42,sy),(sx+51,sy-17),(sx+83,sy-17),(sx+94,sy-32),
            (sx+115,sy-32),(sx+127,sy-18),(sx+156,sy-18),(sx+174,sy)), 3, 1.55)
    p.path(((sx+100,sy-32),(sx+100,sy-56),(sx+112,sy-56)), 3, 1.25)
    for j in range(3):
        p.path(((sx+20+j*7,sy+31+j*5),(sx+w-39-j*11,sy+31+j*5)), 3, .7)
    for j in range(4):
        p.path(((sx+160+j*5,sy-22),(sx+155+j*9,sy-35),
                (sx+174+j*7,sy-48),(sx+184+j*8,sy-58)), 2, 1.1)
    p.text("BENGHAZI NAVAL BASE", "news12", x+10, y+16, .88, ink=3)


def factory_plate(p, x, y, w, h):
    chart_ground(p, x, y, w, h)
    sx, sy = x+22, y+103
    right = x+w-22
    p.path(((sx,sy),(sx,sy-36),(sx+26,sy-55),(sx+26,sy-36),
            (sx+60,sy-55),(sx+60,sy-36),(sx+94,sy-55),(sx+94,sy-36),
            (right,sy-36),(right,sy),(sx,sy)), 3, 1.55)
    for i in range(5):
        p.frame(sx+12+29*i,sy-29,18,12,3)
    for i in range(0, w-49, 6):
        p.path(((sx+i,sy-10),(sx+i+4,sy-4)), 3, .7)
    p.path(((right-39,sy-38),(right-39,sy-77),(right-20,sy-77),(right-20,sy-38)), 3, 1.3)
    for j in range(4):
        p.path(((right-30+j*3,sy-79),(right-40+j*6,sy-91),(right-26+j*5,sy-102)), 2, 1.0)
    p.rule(x+16, y+113, w-32, 3, .7)
    p.text("BANTEN, JAVA", "news12", x+10, y+17, .88, ink=3)


FIGURES = (climate_plate, ship_plate, factory_plate)
# Simplified coastlines in longitude/latitude, used only to locate the numbered reports.
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
MAP_LOCATIONS = (
    ("01", 30.7, 36.9, 16, -14), ("02", 20.1, 32.1, -14, 14),
    ("03", 106.1, -6.1, 14, 13), ("04", 30.5, 50.4, 15, -22),
    ("05", -76.0, -10.9, 3, 16), ("06", 127.0, 37.5, 13, -12),
    ("08", 6.2, 4.8, -5, 12), ("09", -84.4, 33.6, -13, -13),
)


def world_map(p):
    x, y, width, height = 688, 531, 304, 105
    p.frame(x, y, width, height)
    p.text("WORLD MAP", "news12", x+8, y+14, 1.05, ink=3)
    p.text("NUMBERS MATCH STORIES", "news12", x+width-8, y+14, .86, align=1, ink=4)

    def project(lon, lat):
        return x + 11 + (lon + 180) * (width - 22) / 360, y + 21 + (83 - lat) * .52

    for lat in (-30, 0, 30, 60):
        p.path((project(-178,lat), project(178,lat)), 6, .65)
    for coast in COASTS:
        p.path(tuple(project(lon,lat) for lon,lat in coast), 4, .88)
    for number, lon, lat, dx, dy in MAP_LOCATIONS:
        xx, yy = project(lon, lat)
        p.path(((xx,yy),(xx+dx*.78,yy+dy*.78)), 2, .65)
        p.box(xx-1.5, yy-1.5, 3, 3, 2)
        p.box(xx+dx-7, yy+dy-5, 14, 10, 6)
        p.text(number, "news12", xx+dx, yy+dy+3, .81, align=.5, ink=2)


def desk_mark(p, x, y, index, ink):
    marks = (
        ((0,9),(6,3),(12,9),(12,17),(0,17),(0,9),(12,9)),
        ((0,12),(4,12),(7,4),(10,17),(13,7),(16,12),(21,12)),
        ((1,4),(19,4),(19,17),(1,17),(1,4),(10,8),(19,4)),
        ((0,11),(5,11),(5,5),(16,5),(16,11),(21,11),(21,17),(0,17),(0,11)),
        ((0,10),(5,13),(17,13),(22,8),(18,17),(4,17),(0,10)),
        ((0,11),(12,11),(20,5),(17,11),(20,17),(13,13),(3,16),(0,11)),
        ((1,15),(1,10),(17,10),(21,15),(1,15),(6,6),(16,6),(18,10)),
        ((5,3),(18,3),(18,11),(11,17),(5,11),(5,3)),
    )
    p.path(tuple((x+a,y+b) for a,b in marks[index]), ink, 1.2)


def compose(data):
    if len(data["leads"]) != 3 or len(data["desk"]) != 8:
        raise ValueError("The edition needs three lead stories and eight illustrated reports")
    if len(data["briefs"]) != 3 or any(len(items) != 8 for _, _, items in data["briefs"]):
        raise ValueError("Each of the three lower columns needs eight briefs")
    if not 4 <= len(data["numbers"]) <= 6 or len(data["markets"]) != 4:
        raise ValueError("Unexpected number of figures or market references")
    p = Press()
    p.rule(29, 22, 966, 1, 2)
    p.text("THE WORLD DISPATCH", "display22", 31, 46, .95, ink=2)
    p.text("INTERNATIONAL EDITION", "news12", 993, 44, 1.12, align=1, ink=3)
    p.rule(30, 53, 964, 5)
    p.text("22 NOVEMBER 2026", "display55", 512, 118, 1.49, .95, .5, wear=True, limit=960)
    p.text(data["summary"], "news14", 512, 145, 1.19, align=.5, limit=952)
    p.rule(30, 155, 964, 1, 1.5)
    cells = data["numbers"]
    width = 964 / len(cells)
    for i, (value, title) in enumerate(cells):
        x = 30 + width*i
        if i:
            p.box(x, 161, 1, 52, 5)
        p.text(value, "display27", x+width/2, 189, 1.11, align=.5, ink=2, limit=width-18)
        p.text(title, "news12", x+width/2, 205, 1.05, align=.5, limit=width-12)
    p.rule(30, 219, 964, 1, 1.5)

    dimensions = ((30,414),(461,258),(736,258))
    for index, (article, (x,w)) in enumerate(zip(data["leads"], dimensions, strict=True)):
        label, titles, body, source = article
        p.text(f"0{index+1}  /  {label}", "news12", x+1, 240, 1.22, ink=2 if index == 0 else 3)
        FIGURES[index](p, x+1, 247, w-2, 126)
        for row, title in enumerate(titles):
            p.text(title, "display55" if index == 0 else "display27", x, 408+row*30,
                   .77 if index == 0 else 1.08, .95, wear=True, limit=w-4)
        for row, line in enumerate(body):
            p.text(line, "news14", x+1, 461+row*16, 1.11, limit=w-5)
        p.text(source, "news12", x+1, 510, .96, ink=3, limit=w-4)
        if index < 2:
            p.box(x+w+8, 231, .8, 283, 5)

    p.rule(30, 518, 964, 1, 1.6)
    p.text("Around the World", "display27", 30, 545, 1.13)
    p.text("REPORTS 04-11", "news12", 669, 544, .94, align=1, ink=3)
    for index, (section, title, detail) in enumerate(data["desk"]):
        row, col = divmod(index, 2)
        x, y = 30+col*326, 553+row*52
        color = SECTION[section]
        p.rule(x, y, 310, 5, .9)
        desk_mark(p, x+2, y+14, index, color)
        p.text(f"{index+4:02} / {section.upper()}", "news12", x+31, y+12, .92, ink=color)
        p.text(title, "display22", x+30, y+29, .87, limit=280)
        p.text(detail, "news14", x+31, y+44, 1.03, limit=280)
    world_map(p)
    p.frame(688, 645, 304, 108)
    p.text(data["market_label"], "news12", 697, 662, 1.02, ink=3, limit=278)
    for row, (name, value) in enumerate(data["markets"]):
        y = 680+18*row
        p.rule(698, y-11, 284, 6, .75)
        p.text(name, "news14", 700, y, 1.01)
        p.text(value, "news14", 979, y, 1.07, align=1, ink=2)

    p.rule(30, 767, 964, 1, 1.6)
    for col, (name, category, items) in enumerate(data["briefs"]):
        x = 30+col*326
        color = SECTION[category]
        p.rule(x, 774, 312, color, 3)
        p.text(name, "display22", x, 800, 1.07, ink=color)
        for row, item in enumerate(items):
            y = 820+23*row
            p.text(str(12+col*8+row), "news12", x+1, y, .93, ink=color)
            p.text(item, "news14", x+23, y, 1.08, limit=288)
            p.rule(x, y+6, 310, 5, .68)
    p.text("SUNDAY  /  22 NOV 2026", "news12", 30, 1009, .95, ink=3)
    p.text("DATES CHECKED IN LOCAL TIME AND UTC", "news12", 994, 1009, .95, align=1, ink=3)
    return p.plate


def paper_tone(random, x, y):
    edge = min(x, y, SIDE-1-x, SIDE-1-y)
    fold = 2 if 505 <= x <= 510 else 0
    stain = round(2*math.cos(x/174 + y/246) + 2*math.sin(y/83) - 2*math.cos((x-y)/215))
    aging = max(0, 26-edge) * (3 + ((x*19 + y*31) % 5)) // 14
    if edge < 15 and (x + y*3) % 13 == 0:
        aging += 4
    grain = random.randrange(6) - 3
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
