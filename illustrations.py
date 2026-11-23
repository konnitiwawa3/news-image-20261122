"""Paint spot art in a shared 160 by 64 coordinate space."""

from itertools import pairwise
from math import ceil, cos, pi, sin
from random import Random


class ArtBox:
    def __init__(self, plate, x, y, width, height):
        self.plate = plate
        self.origin = x, y
        self.scale = width / 160, height / 64

    def page_point(self, x, y):
        left, top = self.origin
        across, down = self.scale
        return left + x * across, top + y * down

    def fill(self, ink, x, y, width, height):
        across, down = self.scale
        left, top = self.page_point(x, y)
        self.plate.rectangle(left, top, width * across, height * down, ink)

    def ground(self, ink):
        self.fill(ink, 0, 0, 160, 64)

    def polygon(self, ink, *coordinates):
        vertices = tuple(zip(coordinates[::2], coordinates[1::2], strict=True))
        self.fill_polygon(ink, vertices)

    def fill_polygon(self, ink, vertices):
        edges = tuple(pairwise((*vertices, vertices[0])))
        top = ceil(min(y for _, y in vertices) * 3)
        bottom = ceil(max(y for _, y in vertices) * 3)
        for scan in range(top, bottom):
            ordinate = (scan + .5) / 3
            intersections = []
            for (ax, ay), (bx, by) in edges:
                if min(ay, by) <= ordinate < max(ay, by):
                    intersections.append(ax + (bx - ax) * (ordinate - ay) / (by - ay))
            intersections.sort()
            for index in range(0, len(intersections), 2):
                left, right = intersections[index:index + 2]
                self.fill(ink, left, scan / 3, right - left, 1 / 3)

    def stroke(self, ink, weight, *coordinates):
        points = (self.page_point(x, y) for x, y in
                  zip(coordinates[::2], coordinates[1::2], strict=True))
        self.plate.polyline(tuple(points), ink, weight)

    def disk(self, ink, x, y, rx, ry):
        shape = []
        for step in range(36):
            angle = step * pi / 18
            shape.append((x + rx * cos(angle), y + ry * sin(angle)))
        self.fill_polygon(ink, tuple(shape))

    def stipple(self, ink, seed, left, top, width, height, count):
        rng = Random(seed)
        for _ in range(count):
            x = rng.uniform(left, left + width - .55)
            y = rng.uniform(top, top + height - .35)
            span = rng.uniform(.18, .55)
            self.fill(ink, x, y, span, .28)


def apartment_block(art, left, roof, width, floors):
    art.fill("night", left, roof, width, 64 - roof)
    art.fill("night2", left + width - 4, roof + 1, 4, 63 - roof)
    for floor in range(floors):
        baseline = roof + 4 + floor * 5
        for window in range(int((width - 5) / 6)):
            lit = (window * 7 + floor * 3 + int(left)) % 5 > 1
            art.fill("sand" if lit else "slate", left + 3 + window * 6, baseline, 2.5, 2.1)


def damaged_apartments(art):
    art.ground("night")
    art.polygon("night2", 0,34, 24,32, 49,38, 83,30, 119,34, 160,28, 160,64, 0,64)
    art.stipple("slate", 1, 0, 0, 160, 37, 820)
    art.disk("sun", 132, 12, 5, 5)
    skyline = [(4, 42, 21, 4), (25, 47, 21, 3), (49, 38, 21, 5),
               (111, 47, 20, 3), (132, 40, 23, 4)]
    for block in skyline:
        apartment_block(art, *block)
    art.polygon("slate", 70,34, 99,33, 105,40, 104,60, 70,60)
    art.polygon("steel", 70,34, 83,33, 81,57, 70,60)
    art.polygon("night", 86,33, 97,34, 92,39, 98,42, 91,45, 99,51, 93,58, 84,57)
    for column in [74, 81, 100]:
        for row in range(39, 52, 6):
            lit = (column + row) % 3 != 0
            art.fill("sun" if lit else "night2", column, row, 3, 2)
    art.polygon("umber", 71,60, 83,54, 91,59, 96,55, 108,62, 108,64, 70,64)
    for column, row, span in [(23, 12, 5), (61, 19, 7), (103, 9, 4)]:
        art.stroke("flame", 1, column - 12, row - 5, column - 2, row)
        art.polygon("cream", column-span,row-2, column-1,row-1, column+1,row-3, column+2,row,
                    column+span,row+3, column+1,row+2, column-1,row+4, column-2,row+1)
    art.stipple("sand", 4, 72, 55, 33, 9, 135)


def conference_table(art):
    art.ground("sky")
    art.fill("mist", 0, 0, 160, 22)
    for seam in range(6, 160, 26):
        art.fill("cream", seam, 0, 2, 25)
        art.stroke("steel", .6, seam, 18, seam + 24, 18)
    art.disk("pine", 81, 20, 19, 15)
    art.polygon("leaf", 65,14, 78,8, 83,13, 79,22, 69,23)
    art.polygon("leaf", 85,20, 94,17, 97,22, 94,28, 85,33, 84,27)
    art.stroke("mist", .6, 82,6, 82,35)
    art.stroke("mist", .6, 64,20, 99,20)
    art.fill("sand", 0, 38, 160, 26)
    delegates = [(20,38,"night2"), (36,35,"pine"), (53,40,"brick"),
                 (109,40,"night2"), (126,35,"brick"), (144,38,"pine")]
    for x, y, jacket in delegates:
        art.disk(jacket, x, y + 10, 7, 8)
        art.disk("umber", x, y, 3.5, 4)
    art.polygon("brick", 18,44, 139,44, 160,54, 0,54)
    art.fill("night2", 0, 54, 160, 10)
    art.polygon("white", 53,46, 101,46, 112,58, 44,58)
    for inset in range(3):
        y = 49 + inset * 3
        art.stroke("steel", .55, 56 - inset * 2, y, 102 + inset * 2, y)
    art.stroke("rust", 1.5, 68,52, 90,52)


def coastal_radar(art):
    art.ground("sky")
    art.fill("ocean", 0, 40, 160, 24)
    art.polygon("sand", 64,32, 100,30, 160,41, 160,64, 112,64, 87,49, 60,47)
    art.disk("cream", 121, 12, 6, 6)
    art.polygon("night2", 0,47, 55,47, 71,57, 64,64, 0,64)
    art.stroke("steel", 1.7, 33,45, 33,31)
    art.polygon("slate", 17,20, 45,30, 40,38, 29,37, 22,31)
    art.stroke("cream", 1.5, 17,20, 45,30)
    art.stroke("pine", 1, 29,30, 39,19)
    art.disk("cream", 39, 19, 1.7, 1.4)
    for x, y in [(104, 37), (128, 42)]:
        art.fill("umber", x - 8, y, 16, 13)
        art.disk("cream", x, y, 8, 3)
        art.fill("sand", x - 5, y + 3, 3, 9)
    art.fill("brick", 145, 27, 4, 21)
    art.polygon("rust", 120,41, 114,35, 120,27, 124,30, 126,22, 129,34, 125,40)
    art.polygon("flame", 119,40, 119,33, 124,29, 126,36, 123,41)
    for x, y, radius in [(128, 21, 5), (132, 17, 6), (141, 13, 7)]:
        art.disk("slate", x, y, radius, radius / 2)
    for stripe in range(45, 108, 5):
        art.fill("cream", stripe, 53, 2, 1)
    art.stipple("steel", 3, 1, 42, 58, 18, 260)


def industrial_fire(art):
    art.ground("sky")
    art.fill("steel", 0, 50, 160, 14)
    plumes = [(115, 17, 21, 9), (131, 12, 26, 8), (146, 7, 12, 5)]
    for plume in plumes:
        art.disk("slate", *plume)
    art.fill("brick", 123, 25, 8, 24)
    art.polygon("brick", 13,54, 13,39, 40,24, 40,37, 64,24, 64,37,
                87,24, 87,37, 113,29, 113,54)
    for window in range(20, 108, 18):
        art.fill("cream", window, 42, 11, 6)
    art.polygon("flame", 91,36, 86,30, 92,24, 93,29, 102,19, 107,32, 103,36)
    art.polygon("sun", 94,36, 94,31, 100,27, 103,33, 101,36)
    art.stipple("umber", 3, 10, 54, 146, 8, 235)


def harbor_ship(art):
    art.ground("sky")
    art.polygon("sand", 0,32, 21,25, 56,32, 80,32, 104,29, 160,39, 160,44, 0,44)
    art.fill("ocean", 0, 43, 160, 21)
    art.polygon("night2", 13,43, 147,43, 126,57, 31,57)
    art.polygon("slate", 40,43, 50,33, 70,33, 77,24, 99,24, 107,34, 129,35, 134,43)
    art.stroke("night", 1.3, 88,24, 88,10, 104,10)
    art.stroke("night", 1, 87,18, 100,18)
    art.stroke("cream", .8, 24,47, 135,47)
    for ripple in range(14, 143, 18):
        art.stroke("sky", .7, ripple, 60, ripple + 10, 60)
    art.disk("rust", 118, 34, 4, 4)


def city_ballot(art):
    art.ground("mist")
    towers = [(7, 21, 20), (32, 30, 18), (51, 13, 20), (116, 24, 18), (138, 33, 19)]
    for left, roof, span in towers:
        art.fill("steel", left, roof, span, 64 - roof)
        for window in (5, 11, 17):
            art.fill("cream", left + 4, roof + window, 3, 2)
    art.polygon("brick", 59,31, 98,31, 112,39, 65,39)
    art.fill("rust", 65, 39, 47, 25)
    art.stroke("cream", 1, 72,36, 103,36)
    art.polygon("white", 68,12, 102,8, 107,31, 73,37)
    art.stroke("pine", 2.5, 78,24, 84,28, 96,17)


def exam_sheet(art):
    art.ground("sand")
    art.polygon("umber", 0,50, 160,30, 160,64, 0,64)
    art.polygon("white", 21,7, 100,4, 120,52, 37,61)
    for row in range(5):
        left = 36 + row * 2
        right = 90 + row * 3
        y = 18 + row * 7
        art.stroke("steel", .7, left, y, right, y - 4)
    art.polygon("pine", 55,56, 111,11, 118,13, 65,59, 52,62)
    art.polygon("sun", 55,56, 65,59, 52,62)


def night_race(art):
    art.ground("purple15")
    towers = [(2, 18, 19, 31), (25, 23, 17, 26), (45, 12, 13, 37),
              (110, 19, 14, 30), (130, 10, 25, 39)]
    for left, top, width, height in towers:
        art.fill("purple30", left, top, width, height)
        for window in (5, 11, 17):
            art.fill("sun", left + 4, top + window, 2, 2)
    art.fill("slate", 0, 49, 160, 15)
    art.polygon("rust", 16,48, 50,42, 57,31, 74,31, 89,40, 137,43, 143,53, 16,53)
    art.polygon("night2", 59,33, 71,33, 80,41, 56,41)
    for axle in [43, 115]:
        art.disk("night", axle, 52, 10, 8)
        art.disk("steel", axle, 52, 4, 3)
    art.stroke("sun", 1.2, 19,46, 53,45, 83,43, 131,47)


def cricket_pitch(art):
    art.ground("sky")
    art.polygon("pine", 0,30, 73,19, 160,29, 160,64, 0,64)
    art.polygon("leaf", 0,46, 63,36, 143,41, 160,64, 0,64)
    art.polygon("sand", 54,64, 68,42, 97,42, 118,64)
    for stump in range(68, 81, 6):
        art.fill("cream", stump, 23, 1.7, 27)
    art.fill("cream", 67, 23, 15, 2)
    art.polygon("sun", 96,50, 117,18, 121,19, 105,52)
    art.disk("rust", 124, 50, 6, 5)
    art.stroke("cream", .7, 121,47, 124,50, 125,53)


def river_boat(art):
    art.ground("mist")
    art.polygon("leaf", 0,31, 16,18, 40,29, 57,19, 83,32, 123,18, 160,28, 160,40, 0,40)
    art.fill("ocean", 0, 38, 160, 26)
    art.polygon("brick", 35,41, 113,41, 120,53, 106,56, 55,55)
    art.polygon("sand", 38,42, 108,42, 113,48, 43,48)
    ripple_starts = [(8, 53), (23, 44), (59, 59), (115, 59), (129, 48)]
    for x, y in ripple_starts:
        art.stroke("mist", 1, x, y, x + 17, y)
    art.stroke("night2", 1.7, 75,33, 84,43)


def mountain_tremor(art):
    art.ground("sky")
    art.polygon("slate", 0,45, 23,22, 40,30, 73,9, 92,36, 117,17, 160,47, 160,64, 0,64)
    art.polygon("mist", 56,23, 73,9, 86,29, 76,25, 67,29, 66,22)
    art.polygon("pine", 0,43, 32,37, 61,46, 93,39, 130,46, 160,39, 160,64, 0,64)
    art.stroke("cream", 1.5, 5,51, 40,51, 45,45, 50,56, 56,50, 72,50,
               79,35, 85,60, 91,44, 97,53, 104,51, 155,51)


def chamber_dome(art):
    art.ground("sky")
    art.fill("pine", 0, 47, 160, 17)
    art.fill("sand", 25, 42, 112, 17)
    art.fill("cream", 45, 32, 71, 26)
    art.disk("white", 80, 31, 21, 19)
    art.fill("slate", 62, 30, 37, 2)
    art.fill("cream", 76, 12, 8, 5)
    art.stroke("night", 1, 80,12, 80,6)
    for pillar in range(51, 113, 10):
        art.fill("umber", pillar, 42, 2, 13)
    art.fill("steel", 28, 58, 107, 3)


def runway_departure(art):
    art.ground("sky")
    art.polygon("mist", 0,22, 28,18, 61,25, 108,12, 160,19, 160,38, 0,34)
    art.fill("slate", 0, 52, 160, 12)
    for dash in range(9, 147, 18):
        art.fill("cream", dash, 58, 10, 1.5)
    art.polygon("white", 16,39, 47,39, 64,35, 88,20, 98,20, 90,34, 130,27,
                146,30, 138,35, 93,44, 81,50, 72,51, 74,45, 28,46)
    art.polygon("brick", 27,40, 18,28, 27,27, 43,40, 73,39, 132,31, 137,34, 73,44, 28,45)
    art.disk("night2", 111, 36, 4, 2)


def coastal_flood(art):
    art.ground("steel")
    art.polygon("pine", 0,49, 19,23, 48,35, 77,43, 101,27, 119,22, 159,43, 160,64, 0,64)
    art.polygon("ocean", 0,52, 35,44, 82,49, 124,44, 160,50, 160,64, 0,64)
    art.fill("sand", 100, 32, 22, 16)
    art.polygon("brick", 95,34, 111,23, 127,34)
    art.fill("white", 114, 38, 4, 5)
    for drop in range(7, 157, 12):
        art.stroke("sky", .75, drop, 8, drop - 4, 19)
    for ripple in [17, 43, 69, 96, 124]:
        art.stroke("mist", .75, ripple, 55, ripple + 17, 54)


def case_file(art):
    art.ground("red75")
    art.polygon("brick", 0,52, 79,31, 160,47, 160,64, 0,64)
    art.polygon("cream", 37,13, 88,9, 113,55, 51,62)
    art.stroke("slate", 1.6, 48,20, 88,17)
    for row in range(5):
        shift = 2 * row
        y = 25 + 5 * row
        art.stroke("umber", .7, 51 + shift, y, 90 + shift, y - 2)
    art.disk("night2", 105, 30, 14, 13)
    art.disk("sky", 105, 30, 10, 9)
    art.stroke("night2", 3.4, 116,38, 132,53)


SPOT_ART = {
    "dymer": damaged_apartments,
    "summit": conference_table,
    "radar": coastal_radar,
    "factory": industrial_fire,
    "ship": harbor_ship,
    "ballot": city_ballot,
    "exam": exam_sheet,
    "racing": night_race,
    "cricket": cricket_pitch,
    "boat": river_boat,
    "quake": mountain_tremor,
    "capitol": chamber_dome,
    "flight": runway_departure,
    "flood": coastal_flood,
    "poland": case_file,
}
