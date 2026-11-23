"""Build the newspaper's ink plate and print an RGB PNG using only local assets."""

import json
import os
import struct
import zlib
from functools import lru_cache
from itertools import pairwise
from math import cos, sin
from pathlib import Path
from random import Random

from illustrations import ArtBox, SPOT_ART


ASSET_DIR = Path(__file__).resolve().parent
PIXELS = 1024
SUBPIXELS = 3
STRIDE = PIXELS * SUBPIXELS
STOCK_RGB = (246, 236, 213)
EDITION_SEED = 20261122
PNG_LIMIT = 1 << 20

SPOT_INKS = {
    "paper": "f8efd9",
    "rule": "c5b68f",
    "faint": "e7dac0",
    "warm": "70554a",
    "wear1": "463731",
    "wear2": "3f2e31",
    "wear3": "584138",
    "night": "182335",
    "night2": "2c3b50",
    "slate": "596c7b",
    "steel": "899da6",
    "sky": "bacccd",
    "mist": "d4dcd1",
    "sun": "e4ba61",
    "sand": "ccae7a",
    "umber": "8e6e55",
    "rust": "a04d38",
    "flame": "d77846",
    "brick": "743c35",
    "ocean": "416e78",
    "pine": "3c6559",
    "leaf": "729179",
    "grass": "a8aa74",
    "cream": "eee5c9",
    "white": "fbf7ed",
}

# Stone Light print swatches at stops 15, 30, 75, and 95.
THEME_INKS = (
    ("neutral", "25252a 46464e 919197 f0f0f7"),
    ("red", "381d19 603c37 d8ada6 ffece9"),
    ("blue", "17263a 344861 a4bbda e8f2ff"),
    ("teal", "112b24 2c4f44 a1c1b6 e6f5ef"),
    ("purple", "2a2135 4c405b beb2d2 f4edff"),
    ("orange", "36200d 5e3f27 d7b18d ffeddd"),
    ("cyan", "0c2a31 264d57 99c1cb def6fc"),
)


def build_inks():
    palette = dict(SPOT_INKS)
    for family, ramp in THEME_INKS:
        palette.update((family + stop, color) for stop, color in
                       zip(("15", "30", "75", "95"), ramp.split(), strict=True))
    indices = {ink: slot for slot, ink in enumerate(palette, start=1)}
    rgb = [b""] + [bytes.fromhex(hex_rgb) for hex_rgb in palette.values()]
    return indices, rgb


INK_ID, INK_RGB = build_inks()
BODY_INK = "neutral15"
ACCENT = "red30"
SMALL_INK = "blue30"
NEWS_SMALL = "news12"


class InkPlate:
    def __init__(self):
        self.dots = bytearray(STRIDE ** 2)
        glyph_file = ASSET_DIR / "materials" / "glyphs.json.z"
        self.typecase = json.loads(zlib.decompress(glyph_file.read_bytes()))

    @lru_cache(maxsize=4096)
    def glyph_dots(self, face, letter, sx, sy):
        _, bearing, ascent, width, height, packed_bits = self.typecase[face][letter]
        bitmap = bytes.fromhex(packed_bits)
        row_bytes = (width + 7) // 8
        x0, y0 = round(bearing * sx), round(ascent * sy)
        columns = [min(int(x / sx), width - 1) for x in range(round(width * sx))]
        samples = [divmod(column, 8) for column in columns]
        dots = []
        for y in range(round(height * sy)):
            row = row_bytes * min(int(y / sy), height - 1)
            for x, (octet, bit) in enumerate(samples):
                if (bitmap[row + octet] << bit) & 0x80:
                    dots.append((x0 + x, y0 + y))
        return tuple(dots)

    def advances(self, text, face, size, stretch):
        font = self.typecase[face]
        return [round(font[letter][0] * size * stretch) for letter in text]

    def measure(self, text, face, size):
        return sum(self.advances(text, face, size, 1)) / SUBPIXELS

    def print_text(self, text, face, x, y, size=1, stretch=1, anchor=0,
                   color=BODY_INK, distressed=False, limit=None):
        steps = self.advances(text, face, size, stretch)
        span = sum(steps) / SUBPIXELS
        if limit is not None and span > limit:
            if limit / span < .73:
                raise ValueError(f"Line will not fit its measure: {text!r}")
            return self.print_text(text, face, x, y, size, stretch * (limit - 1) / span,
                                   anchor, color, distressed)

        pen = round((x - anchor * span) * SUBPIXELS)
        baseline = round(y * SUBPIXELS)
        letter_width = size * stretch
        ink = INK_ID[color]
        for index, letter in enumerate(text):
            if distressed:
                noise = (2654435761 * (EDITION_SEED + pen + baseline * 1031 + index * 29)) & 0xffffffff
                ink = INK_ID["wear" + str(1 + (noise >> 8) % 3)]
            for dx, dy in self.glyph_dots(face, letter, letter_width, size):
                column, row = pen + dx, baseline + dy
                if not (0 <= column < STRIDE and 0 <= row < STRIDE):
                    continue
                if distressed and (noise + column // 2 * 13 + row // 2 * 7) % 113 < 4:
                    continue
                offset = row * STRIDE + column
                self.dots[offset] = ink
                if distressed and row + 2 < STRIDE and (noise + column * 7 + row) % 31 < 3:
                    bleed = offset + 2 * STRIDE
                    if self.dots[bleed] == 0:
                        self.dots[bleed] = INK_ID["rule"]
            pen += steps[index]
        return span

    def rectangle(self, x, y, width, height, color):
        left = round(x * SUBPIXELS)
        top = round(y * SUBPIXELS)
        right = round((x + width) * SUBPIXELS)
        bottom = round((y + height) * SUBPIXELS)
        if not (0 <= left <= STRIDE and 0 <= top <= STRIDE and right <= STRIDE and bottom <= STRIDE):
            raise ValueError(f"Rectangle exceeds the plate: {(x, y, width, height)!r}")
        stripe = bytes([INK_ID[color]]) * (right - left)
        for line in range(top * STRIDE, bottom * STRIDE, STRIDE):
            self.dots[line + left:line + right] = stripe

    def polyline(self, points, color, weight):
        half = weight / 2
        for (x, y), (end_x, end_y) in pairwise(points):
            dx, dy = end_x - x, end_y - y
            subdivisions = max(1, round(SUBPIXELS * max(abs(dx), abs(dy))))
            for position in range(subdivisions + 1):
                left = x + dx * position / subdivisions - half
                top = y + dy * position / subdivisions - half
                self.rectangle(left, top, weight, weight, color)

    def rule(self, x, y, width, color=BODY_INK, weight=1):
        self.rectangle(x, y, width, weight, color)

    def frame(self, x, y, width, height, color):
        right, bottom = x + width, y + height
        outline = [(x, y), (right, y), (right, bottom), (x, bottom), (x, y)]
        self.polyline(outline, color, .8)

    def spot(self, name, x, y, width, height):
        SPOT_ART[name](ArtBox(self, x, y, width, height))


def stock_offset(x, y, noise):
    margin = min(x, y, PIXELS - 1 - x, PIXELS - 1 - y)
    crease = 2 if 505 <= x <= 510 else 0
    waves = 2 * cos(x / 174 + y / 246) + 2 * sin(y / 83) - 2 * cos((x - y) / 215)
    aging = max(0, 26 - margin) * (3 + (19 * x + 31 * y) % 5) // 14
    if margin < 15 and (x + 3 * y) % 13 == 0:
        aging += 4
    return max(-40, min(11, noise.randrange(4) - 2 + round(waves) - aging - crease))


def mix_ink(ground, ink_ids):
    pigments = [INK_RGB[slot] for slot in ink_ids if slot]
    clear = SUBPIXELS ** 2 - len(pigments)
    channels = []
    for channel, stock in enumerate(ground):
        total = clear * stock + sum(rgb[channel] for rgb in pigments)
        channels.append((total + 4) // 9)
    return bytes(channels)


def rgb_scanlines(dots):
    noise = Random(EDITION_SEED)
    paper = [bytes(min(255, max(0, channel + shift)) for channel in STOCK_RGB)
             for shift in range(-40, 12)]
    ink_cache = {}
    unprinted = bytes(SUBPIXELS ** 2)
    for scan in range(PIXELS):
        start = scan * SUBPIXELS * STRIDE
        a, b, c = [dots[start + i * STRIDE:start + (i + 1) * STRIDE] for i in range(SUBPIXELS)]
        rgb = bytearray()
        for x in range(PIXELS):
            sample = slice(x * SUBPIXELS, (x + 1) * SUBPIXELS)
            coverage = a[sample] + b[sample] + c[sample]
            shade = stock_offset(x, scan, noise)
            ground = paper[shade + 40]
            if coverage == unprinted:
                rgb.extend(ground)
                continue
            ranks = bytes(sorted(coverage))
            key = (shade, ranks)
            if key not in ink_cache:
                ink_cache[key] = mix_ink(ground, ranks)
            rgb.extend(ink_cache[key])
        yield rgb


def chunk(tag, payload):
    block = tag + payload
    return struct.pack(">I", len(payload)) + block + struct.pack(">I", zlib.crc32(block))


def save_png(path, dots):
    encoder = zlib.compressobj(9)
    image_data = bytearray()
    for rgb in rgb_scanlines(dots):
        scanline = bytes([1]) + rgb[:3]
        scanline += bytes((pixel - previous) & 0xff for previous, pixel in zip(rgb, rgb[3:]))
        image_data.extend(encoder.compress(scanline))
    image_data.extend(encoder.flush())

    header = struct.pack(">2I5B", PIXELS, PIXELS, 8, 2, 0, 0, 0)
    result = b"".join((b"\x89PNG\r\n\x1a\n", chunk(b"IHDR", header),
                       chunk(b"IDAT", bytes(image_data)), chunk(b"IEND", b"")))
    if len(result) > PNG_LIMIT:
        raise ValueError(f"PNG exceeds the byte limit: {len(result)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result)


PAGE_LEFT, PAGE_RIGHT = 30, 994
PRINT_WIDTH = PAGE_RIGHT - PAGE_LEFT
DISPLAY_SMALL = "display22"
DISPLAY_MEDIUM = "display27"
DISPLAY_LARGE = "display55"

# Longitude and latitude pairs. Closed outlines receive the map's dot fill.
COAST_COORDINATES = (
    """-166 64 -146 60 -129 54 -124 46 -117 32 -101 20 -88 18 -83 10
       -77 8 -81 21 -90 28 -82 30 -76 37 -65 46 -57 52 -67 58 -59 64
       -81 72 -110 72 -134 68 -155 71 -166 64""",
    """-81 10 -67 10 -57 5 -34 -7 -39 -20 -51 -32 -61 -54 -69 -54
       -75 -41 -71 -24 -78 -11 -81 10""",
    "-54 61 -44 60 -23 67 -20 78 -36 83 -61 78 -54 61",
    """-11 36 -9 44 1 50 9 54 17 59 25 71 46 69 62 72 82 73 111 73 134 69
       159 63 177 65 166 55 146 49 142 36 124 35 120 22 109 18 104 2 96 7 90 23 79 10
       71 19 66 26 56 26 48 30 36 35 31 41 22 39 16 39 9 44 3 43 -2 36 -11 36""",
    """-17 13 -17 26 -6 35 12 36 26 32 33 30 43 12 51 11 47 1 40 -11 34 -19
       25 -34 18 -34 12 -19 11 -7 5 5 -7 5 -17 13""",
    "95 5 105 1 109 -6 121 -9 132 -8",
    "114 5 118 -3 124 1",
    "112 -22 123 -14 135 -13 145 -12 154 -27 151 -36 141 -39 131 -31 115 -34 112 -22",
    "132 34 137 36 141 42 143 45",
    "166 -45 172 -42 178 -36",
)

ISLANDS = [
    (106, -7), (115, -8), (120, -9), (124, -4), (136, 35), (140, 39),
    (144, 44), (171, -43), (175, -39), (178, -37), (48, -19),
]


def coast_edges():
    for coordinates in COAST_COORDINATES:
        degrees = [int(degree) for degree in coordinates.split()]
        points = list(zip(degrees[::2], degrees[1::2], strict=True))
        if len(points) >= 4 and points[0] == points[-1]:
            yield tuple(pairwise(points))


def on_land(lon, lat, outlines):
    for edges in outlines:
        inside = False
        for (x, y), (xx, yy) in edges:
            if (y <= lat < yy) or (yy <= lat < y):
                crossing = x + (xx - x) * (lat - y) / (yy - y)
                if lon < crossing:
                    inside = not inside
        if inside:
            return True
    return False


class Newspaper:
    def __init__(self, issue):
        self.issue = issue
        self.press = InkPlate()
        self.desk_ink = {name: ramp + "30" for name, ramp in issue["desks"].items()}
        self.desk_count = dict.fromkeys(self.desk_ink, 0)
        for group, expected_size in (("front", 3), ("illustrated", 12), ("wire", 22)):
            articles = issue[group]
            if len(articles) != expected_size:
                raise ValueError(f"{group} must contain {expected_size} articles")
            for article in articles:
                self.desk_count[article["desk"]] += 1

    def stamp(self, number, x, y, color, width):
        self.press.rectangle(x, y, width, 13, color)
        self.press.print_text(f"{number:02d}", NEWS_SMALL, x + width / 2, y + 10,
                              .85, anchor=.5, color="white")

    def set_headline(self, lines, face, x, baseline, width, size, leading):
        measure = max(self.press.measure(line, face, size) for line in lines)
        horizontal_scale = min(1, (width - 1) / measure)
        for line_no, line in enumerate(lines):
            self.press.print_text(line, face, x, baseline + line_no * leading, size, horizontal_scale)

    def masthead(self):
        plate = self.press
        heading = f"SUNDAY EDITION   /   {sum(self.desk_count.values())} STORIES   /   {len(self.desk_count)} REGIONS"
        plate.rule(PAGE_LEFT, 20, PRINT_WIDTH, weight=2)
        plate.print_text("THE WORLD DISPATCH", DISPLAY_SMALL, PAGE_LEFT, 43, color=ACCENT)
        plate.print_text(heading, NEWS_SMALL, PAGE_RIGHT, 42, .97, anchor=1, color=SMALL_INK)
        plate.rule(PAGE_LEFT, 49, PRINT_WIDTH, "rule", .85)
        plate.print_text("22 NOVEMBER 2026", DISPLAY_LARGE, 512, 111, 1.39,
                         anchor=.5, distressed=True, limit=PRINT_WIDTH)
        plate.print_text(self.issue["digest"], "news14", 512, 135, 1.16, anchor=.5, limit=PRINT_WIDTH)
        plate.rule(PAGE_LEFT, 145, PRINT_WIDTH, weight=1.35)
        self.news_in_numbers()
        self.desk_band()
        self.report_clock()

    def news_in_numbers(self):
        plate = self.press
        indicators = self.issue["indicators"]
        cell = PRINT_WIDTH / len(indicators)
        for index, item in enumerate(indicators):
            edge = PAGE_LEFT + index * cell
            midpoint = edge + cell / 2
            if index != 0:
                plate.rectangle(edge, 153, .7, 40, "rule")
            label = "  /  ".join((item["article"], item["caption"]))
            plate.print_text(item["figure"], DISPLAY_MEDIUM, midpoint, 174, 1.07,
                             anchor=.5, color=ACCENT, limit=cell - 8)
            plate.print_text(label, NEWS_SMALL, midpoint, 189, .91,
                             anchor=.5, color=SMALL_INK, limit=cell - 9)

    def desk_band(self):
        plate = self.press
        cell = PRINT_WIDTH / len(self.desk_ink)
        for index, (desk, color) in enumerate(self.desk_ink.items()):
            edge = PAGE_LEFT + index * cell
            label = f"{desk}  {self.desk_count[desk]}"
            plate.rectangle(edge, 201, cell, 20, color)
            plate.print_text(label, NEWS_SMALL, edge + cell / 2, 215, 1.02, anchor=.5, color="white")

    def report_clock(self):
        plate = self.press
        clock = self.issue["clock"]
        plate.rectangle(PAGE_LEFT, 226, PRINT_WIDTH, 19, "paper")
        for y in (226, 244):
            plate.rule(PAGE_LEFT, y, PRINT_WIDTH, "rule", .8)
        plate.print_text("UTC", NEWS_SMALL, PAGE_LEFT + 8, 239.3, 1.06, color=ACCENT)
        cell = (PRINT_WIDTH - 49) / len(clock)
        for index, (hour, (event, _story)) in enumerate(clock.items()):
            edge = PAGE_LEFT + 49 + index * cell
            plate.rectangle(edge - 4, 230, .6, 10, "rule")
            plate.print_text(hour, NEWS_SMALL, edge + 1, 239, .91, color=ACCENT)
            plate.print_text(event, NEWS_SMALL, edge + 38, 239, .85, limit=cell - 43)

    def front_page(self):
        plate = self.press
        columns = ((30, 402), (448, 265), (729, 265))
        for number, (article, (left, width)) in enumerate(zip(self.issue["front"], columns, strict=True), 1):
            color = self.desk_ink[article["desk"]]
            right = left + width
            plate.rule(left, 254, width, color, 2)
            plate.spot(article["art"], left, 256, width, 102)
            self.stamp(number, left, 256, color, 24)
            if number == 3:
                for x, text in ((left + 6, "IRAN'S CLAIM"), (left + width / 2 + 5, "BAHRAIN'S ACCOUNT")):
                    plate.rectangle(x, 341, 103, 13, "paper")
                    plate.print_text(text, NEWS_SMALL, x + 5, 350.5, .78, color=ACCENT)
            plate.print_text(article["dateline"], NEWS_SMALL, left, 375, 1.03, color=color)
            plate.print_text(article["status"], NEWS_SMALL, right, 375, .89, anchor=1, color=color)
            if number == 1:
                self.set_headline(article["display"], DISPLAY_LARGE, left, 405, width, .70, 33)
            else:
                self.set_headline(article["display"], DISPLAY_MEDIUM, left, 406, width, 1.05, 26)
            for row, detail in enumerate(article["deck"]):
                plate.print_text(detail, "news14", left, 459 + row * 15, 1.02, limit=width)
            plate.print_text(article["credit"], NEWS_SMALL, left, 489, .91, color=SMALL_INK, limit=width)
            if number != len(columns):
                plate.rectangle(right + 7, 254, .8, 235, "rule")

    def illustrated_reports(self):
        plate = self.press
        plate.rule(PAGE_LEFT, 499, PRINT_WIDTH, weight=1.3)
        plate.print_text("Around the World", DISPLAY_SMALL, PAGE_LEFT, 520, .98)
        plate.print_text("ILLUSTRATED REPORTS 04-15", NEWS_SMALL, PAGE_RIGHT, 519,
                         .92, anchor=1, color=SMALL_INK)
        gutter = 10
        width = (PRINT_WIDTH - 5 * gutter) / 6
        for index, article in enumerate(self.issue["illustrated"]):
            row, column = divmod(index, 6)
            left, top = PAGE_LEFT + column * (width + gutter), 529 + row * 103
            color = self.desk_ink[article["desk"]]
            plate.rule(left, top, width, color, 2)
            plate.spot(article["art"], left, top + 2, width, 36)
            self.stamp(index + 4, left, top + 2, color, 19)
            plate.print_text(article["dateline"], NEWS_SMALL, left, top + 49, .86, color=color)
            self.set_headline(article["display"], DISPLAY_SMALL, left, top + 64, width, .73, 14)
            plate.print_text(article["deck"], NEWS_SMALL, left, top + 89, .86, limit=width)
            credit = "  /  ".join((article["status"], article["credit"]))
            plate.print_text(credit, NEWS_SMALL, left, top + 99, .75, color=SMALL_INK, limit=width)

    def map_panel(self):
        plate = self.press
        x, y, width, height = PAGE_LEFT, 741, 313, 179
        plate.rectangle(x, y, width, height, "night")
        plate.print_text("WORLD MAP", DISPLAY_SMALL, x + 9, y + 20, .85, color="white")
        plate.print_text("PINS MATCH STORY NUMBERS", NEWS_SMALL, x + width - 9, y + 19,
                         .77, anchor=1, color="sky")
        plate.rule(x + 9, y + 25, width - 18, "slate", .7)

        def project(lon, lat):
            return x + 13 + (lon + 180) * (width - 26) / 360, y + 33 + (84 - lat) * .91

        outlines = tuple(coast_edges())
        for latitude in range(-56, 84, 4):
            for longitude in range(-176, 180, 4):
                if on_land(longitude, latitude, outlines):
                    px, py = project(longitude, latitude)
                    plate.rectangle(px - .78, py - .72, 1.56, 1.44, "blue75")
        for point in ISLANDS:
            px, py = project(*point)
            plate.rectangle(px - .85, py - .85, 1.7, 1.7, "blue75")

        tags = []
        articles = self.issue["front"] + self.issue["illustrated"]
        for number, article in enumerate(articles, 1):
            locator = article["locator"]
            if locator is None:
                continue
            px, py = project(*locator["point"])
            dx, dy = locator["offset"]
            tx, ty = px + dx, py + dy
            plate.polyline(((px, py), (tx, ty)), "sky", .7)
            plate.rectangle(px - 1, py - 1, 2, 2, "white")
            tags.append((number, tx, ty, self.desk_ink[article["desk"]]))
        for number, tx, ty, tint in tags:
            plate.rectangle(tx - 8.5, ty - 6.5, 17, 13, "cream")
            plate.rectangle(tx - 7.5, ty - 5.5, 15, 11, tint)
            plate.print_text(f"{number:02d}", NEWS_SMALL, tx, ty + 3.1, .74, anchor=.5, color="white")
        plate.print_text("SELECTED LOCATIONS  /  NOT TO SCALE", NEWS_SMALL, x + 9, y + height - 7,
                         .78, color="sky")

    def wire_column(self):
        plate = self.press
        x = 357
        plate.rule(x, 741, PAGE_RIGHT - x)
        plate.print_text("Also on Sunday", DISPLAY_SMALL, x, 760, .94)
        plate.print_text("REPORTS 16-37   /   STATUS & SOURCE AT RIGHT", NEWS_SMALL, PAGE_RIGHT, 759,
                         .86, anchor=1, color=SMALL_INK)
        for index, article in enumerate(self.issue["wire"]):
            column, row = divmod(index, 11)
            left = x + column * 322
            y = 775 + row * 14.1
            color = self.desk_ink[article["desk"]]
            plate.rectangle(left, y - 7.5, 2.4, 8, color)
            plate.print_text(f"{16 + index:02d}", NEWS_SMALL, left + 6, y, .87, color=color)
            credit = " / ".join((article["status"], article["credit"]))
            available = 282 - plate.measure(credit, NEWS_SMALL, .65)
            plate.print_text(article["line"], NEWS_SMALL, left + 24, y, .91, limit=available)
            plate.print_text(credit, NEWS_SMALL, left + 314, y, .65, anchor=1, color=SMALL_INK)
            plate.rule(left, y + 3.8, 314, "faint", .52)

    def closing_strip(self):
        plate = self.press
        plate.rectangle(PAGE_LEFT, 928, PRINT_WIDTH, 38, "paper")
        plate.frame(PAGE_LEFT, 928, PRINT_WIDTH, 38, ACCENT)
        plate.print_text("DATE CHECK", DISPLAY_SMALL, PAGE_LEFT + 10, 950, .75, color=ACCENT)
        plate.rectangle(PAGE_LEFT + 130, 935, .7, 23, "rule")
        for row, note in enumerate(self.issue["chronology_notes"]):
            plate.print_text(note, NEWS_SMALL, PAGE_LEFT + 141, 943 + row * 13, .90,
                             limit=PRINT_WIDTH - 152)
        plate.rule(PAGE_LEFT, 975, PRINT_WIDTH, weight=1.25)
        plate.print_text("MARKETS", DISPLAY_SMALL, PAGE_LEFT, 991, .70, color=SMALL_INK)
        plate.print_text("FRI 20 NOV", NEWS_SMALL, PAGE_LEFT, 1004, .84, color=SMALL_INK)
        for index, (label, quote) in enumerate(self.issue["closing_quotes"].items()):
            left = PAGE_LEFT + 116 + index * 130
            plate.rectangle(left, 981, .7, 25, "rule")
            plate.print_text(label, NEWS_SMALL, left + 9, 990, .82, color=SMALL_INK)
            plate.print_text(quote, DISPLAY_SMALL, left + 9, 1006, .69, color=ACCENT)
        plate.print_text("ORIGINAL SCENE ILLUSTRATIONS", NEWS_SMALL, PAGE_RIGHT, 991, .82,
                         anchor=1, color=SMALL_INK)
        plate.print_text("DATES CHECKED IN LOCAL TIME AND UTC", NEWS_SMALL, PAGE_RIGHT, 1004, .82,
                         anchor=1, color=SMALL_INK)

    def render(self):
        self.masthead()
        self.front_page()
        self.illustrated_reports()
        self.map_panel()
        self.wire_column()
        self.closing_strip()
        return self.press.dots


def main():
    issue_path = ASSET_DIR / "edition.json"
    with issue_path.open(encoding="utf-8") as input_file:
        issue = json.load(input_file)
    output = Path(os.getenv("MAKEFUN_OUTPUT_DIR", "/output"))
    save_png(output / "entry.png", Newspaper(issue).render())


if __name__ == "__main__":
    main()
