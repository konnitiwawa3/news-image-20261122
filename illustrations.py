"""Original spot illustrations for a two-color-to-four-color offset look."""

from math import ceil, cos, pi, sin
from random import Random


class Scene:
    """Draw in a common 160-by-64 art box using the newspaper's ink plate."""

    def __init__(self, press, palette, x, y, width, height):
        self.press = press
        self.palette = palette
        self.x, self.y = x, y
        self.sx, self.sy = width / 160, height / 64

    def rect(self, color, x, y, width, height):
        self.press.box(self.x + x*self.sx, self.y + y*self.sy,
                       width*self.sx, height*self.sy, self.palette[color])

    def base(self, color):
        self.rect(color, 0, 0, 160, 64)

    def ink(self, color, points):
        vertices = (*points, points[0])
        for row in range(ceil(min(v[1] for v in points)*3), ceil(max(v[1] for v in points)*3)):
            y = (row+.5) / 3
            crossings = sorted(x1+(x2-x1)*(y-y1)/(y2-y1)
                               for (x1,y1), (x2,y2) in zip(vertices, vertices[1:])
                               if min(y1,y2) <= y < max(y1,y2))
            for left, right in zip(crossings[::2], crossings[1::2], strict=True):
                self.rect(color, left, row/3, right-left, 1/3)

    def line(self, color, *points, weight=1):
        self.press.path([(self.x + x*self.sx, self.y + y*self.sy) for x,y in points],
                        self.palette[color], weight)

    def oval(self, color, x, y, rx, ry):
        self.ink(color, tuple((x+rx*cos(i*pi/18), y+ry*sin(i*pi/18)) for i in range(36)))

    def grain(self, color, seed, area, count):
        rng = Random(seed)
        x,y,width,height = area
        for _ in range(count):
            self.rect(color, rng.uniform(x,x+width-.55), rng.uniform(y,y+height-.35),
                      rng.uniform(.18,.55), .28)


def blocks(s, x, y, width, rows, stone, window):
    s.rect(stone, x, y, width, 64-y)
    s.rect("night2", x+width-4, y+1, 4, 63-y)
    for iy in range(rows):
        for ix in range(int((width-5)/6)):
            shade = window if (ix*7+iy*3+int(x)) % 5 > 1 else "slate"
            s.rect(shade, x+3+ix*6, y+4+iy*5, 2.5, 2.1)


def dymer(s):
    s.base("night")
    s.ink("night2", ((0,34),(24,32),(49,38),(83,30),(119,34),(160,28),(160,64),(0,64)))
    s.grain("slate", 1, (0,0,160,37), 820)
    s.oval("sun", 132, 12, 5, 5)
    for x,y,w,h in ((4,42,21,4),(25,47,21,3),(49,38,21,5),(111,47,20,3),(132,40,23,4)):
        blocks(s, x, y, w, h, "night", "sand")
    s.ink("slate", ((70,34),(99,33),(105,40),(104,60),(70,60)))
    s.ink("steel", ((70,34),(83,33),(81,57),(70,60)))
    s.ink("night", ((86,33),(97,34),(92,39),(98,42),(91,45),(99,51),(93,58),(84,57)))
    for x in (74,81,100):
        for y in (39,45,51):
            s.rect("sun" if (x+y)%3 else "night2",x,y,3,2)
    s.ink("umber", ((71,60),(83,54),(91,59),(96,55),(108,62),(108,64),(70,64)))
    for x,y,size in ((23,12,5),(61,19,7),(103,9,4)):
        s.line("flame",(x-12,y-5),(x-2,y),weight=1)
        s.ink("cream", ((x-size,y-2),(x-1,y-1),(x+1,y-3),(x+2,y),
                        (x+size,y+3),(x+1,y+2),(x-1,y+4),(x-2,y+1)))
    s.grain("sand", 4, (72,55,33,9), 135)


def summit(s):
    s.base("sky")
    s.rect("mist",0,0,160,22)
    for x in range(6,160,26):
        s.rect("cream",x,0,2,25)
        s.line("steel",(x,18),(x+24,18),weight=.6)
    s.oval("pine",81,20,19,15)
    s.ink("leaf",((65,14),(78,8),(83,13),(79,22),(69,23)))
    s.ink("leaf",((85,20),(94,17),(97,22),(94,28),(85,33),(84,27)))
    s.line("mist",(82,6),(82,35),weight=.6)
    s.line("mist",(64,20),(99,20),weight=.6)
    s.rect("sand",0,38,160,26)
    for x,y,c in ((20,38,"night2"),(36,35,"pine"),(53,40,"brick"),
                  (109,40,"night2"),(126,35,"brick"),(144,38,"pine")):
        s.oval(c,x,y+10,7,8)
        s.oval("umber",x,y,3.5,4)
    s.ink("brick", ((18,44),(139,44),(160,54),(0,54)))
    s.rect("night2",0,54,160,10)
    s.ink("white", ((53,46),(101,46),(112,58),(44,58)))
    for i in range(3):
        s.line("steel",(56-i*2,49+i*3),(102+i*2,49+i*3),weight=.55)
    s.line("rust",(68,52),(90,52),weight=1.5)


def radar(s):
    s.base("sky")
    s.rect("ocean",0,40,160,24)
    s.ink("sand",((64,32),(100,30),(160,41),(160,64),(112,64),(87,49),(60,47)))
    s.oval("cream",121,12,6,6)
    s.ink("night2",((0,47),(55,47),(71,57),(64,64),(0,64)))
    s.line("steel",(33,45),(33,31),weight=1.7)
    s.ink("slate",((17,20),(45,30),(40,38),(29,37),(22,31)))
    s.line("cream",(17,20),(45,30),weight=1.5)
    s.line("pine",(29,30),(39,19),weight=1)
    s.oval("cream",39,19,1.7,1.4)
    for x,y in ((104,37),(128,42)):
        s.rect("umber",x-8,y,16,13)
        s.oval("cream",x,y,8,3)
        s.rect("sand",x-5,y+3,3,9)
    s.rect("brick",145,27,4,21)
    s.ink("rust",((120,41),(114,35),(120,27),(124,30),(126,22),(129,34),(125,40)))
    s.ink("flame",((119,40),(119,33),(124,29),(126,36),(123,41)))
    for x,y,r in ((128,21,5),(132,17,6),(141,13,7)):
        s.oval("slate",x,y,r,r/2)
    for x in range(45,108,5):
        s.rect("cream",x,53,2,1)
    s.grain("steel", 3, (1,42,58,18), 260)


def factory(s):
    s.base("sky")
    s.rect("steel",0,50,160,14)
    for x,y,rx,ry in ((115,17,21,9),(131,12,26,8),(146,7,12,5)):
        s.oval("slate",x,y,rx,ry)
    s.rect("brick",123,25,8,24)
    s.ink("brick",((13,54),(13,39),(40,24),(40,37),(64,24),(64,37),
                   (87,24),(87,37),(113,29),(113,54)))
    for x in range(20,108,18):
        s.rect("cream",x,42,11,6)
    s.ink("flame",((91,36),(86,30),(92,24),(93,29),(102,19),(107,32),(103,36)))
    s.ink("sun",((94,36),(94,31),(100,27),(103,33),(101,36)))
    s.grain("umber", 3, (10,54,146,8), 235)


def ship(s):
    s.base("sky")
    s.ink("sand",((0,32),(21,25),(56,32),(80,32),(104,29),(160,39),(160,44),(0,44)))
    s.rect("ocean",0,43,160,21)
    s.ink("night2",((13,43),(147,43),(126,57),(31,57)))
    s.ink("slate",((40,43),(50,33),(70,33),(77,24),(99,24),(107,34),(129,35),(134,43)))
    s.line("night",(88,24),(88,10),(104,10),weight=1.3)
    s.line("night",(87,18),(100,18),weight=1)
    s.line("cream",(24,47),(135,47),weight=.8)
    for x in range(14,143,18):
        s.line("sky",(x,60),(x+10,60),weight=.7)
    s.oval("rust",118,34,4,4)


def ballot(s):
    s.base("mist")
    for x,y,w in ((7,21,20),(32,30,18),(51,13,20),(116,24,18),(138,33,19)):
        s.rect("steel",x,y,w,64-y)
        for i in range(3):
            s.rect("cream",x+4,y+5+i*6,3,2)
    s.ink("brick",((59,31),(98,31),(112,39),(65,39)))
    s.rect("rust",65,39,47,25)
    s.line("cream",(72,36),(103,36),weight=1)
    s.ink("white",((68,12),(102,8),(107,31),(73,37)))
    s.line("pine",(78,24),(84,28),(96,17),weight=2.5)


def exam(s):
    s.base("sand")
    s.ink("umber",((0,50),(160,30),(160,64),(0,64)))
    s.ink("white",((21,7),(100,4),(120,52),(37,61)))
    for i in range(5):
        s.line("steel",(36+i*2,18+i*7),(90+i*3,14+i*7),weight=.7)
    s.ink("pine",((55,56),(111,11),(118,13),(65,59),(52,62)))
    s.ink("sun",((55,56),(65,59),(52,62)))


def racing(s):
    s.base("purple15")
    for x,y,w,h in ((2,18,19,31),(25,23,17,26),(45,12,13,37),
                     (110,19,14,30),(130,10,25,39)):
        s.rect("purple30",x,y,w,h)
        for q in range(3):
            s.rect("sun",x+4,y+5+q*6,2,2)
    s.rect("slate",0,49,160,15)
    s.ink("rust",((16,48),(50,42),(57,31),(74,31),(89,40),(137,43),
                  (143,53),(16,53)))
    s.ink("night2",((59,33),(71,33),(80,41),(56,41)))
    for x in (43,115):
        s.oval("night",x,52,10,8)
        s.oval("steel",x,52,4,3)
    s.line("sun",(19,46),(53,45),(83,43),(131,47),weight=1.2)


def cricket(s):
    s.base("sky")
    s.ink("pine",((0,30),(73,19),(160,29),(160,64),(0,64)))
    s.ink("leaf",((0,46),(63,36),(143,41),(160,64),(0,64)))
    s.ink("sand",((54,64),(68,42),(97,42),(118,64)))
    for x in (68,74,80):
        s.rect("cream",x,23,1.7,27)
    s.rect("cream",67,23,15,2)
    s.ink("sun",((96,50),(117,18),(121,19),(105,52)))
    s.oval("rust",124,50,6,5)
    s.line("cream",(121,47),(124,50),(125,53),weight=.7)


def boat(s):
    s.base("mist")
    s.ink("leaf",((0,31),(16,18),(40,29),(57,19),(83,32),(123,18),(160,28),(160,40),(0,40)))
    s.rect("ocean",0,38,160,26)
    s.ink("brick",((35,41),(113,41),(120,53),(106,56),(55,55)))
    s.ink("sand",((38,42),(108,42),(113,48),(43,48)))
    for x,y in ((8,53),(23,44),(59,59),(115,59),(129,48)):
        s.line("mist",(x,y),(x+17,y),weight=1)
    s.line("night2",(75,33),(84,43),weight=1.7)


def quake(s):
    s.base("sky")
    s.ink("slate",((0,45),(23,22),(40,30),(73,9),(92,36),(117,17),(160,47),(160,64),(0,64)))
    s.ink("mist",((56,23),(73,9),(86,29),(76,25),(67,29),(66,22)))
    s.ink("pine",((0,43),(32,37),(61,46),(93,39),(130,46),(160,39),(160,64),(0,64)))
    s.line("cream",(5,51),(40,51),(45,45),(50,56),(56,50),(72,50),
           (79,35),(85,60),(91,44),(97,53),(104,51),(155,51),weight=1.5)


def capitol(s):
    s.base("sky")
    s.rect("pine",0,47,160,17)
    s.rect("sand",25,42,112,17)
    s.rect("cream",45,32,71,26)
    s.oval("white",80,31,21,19)
    s.rect("slate",62,30,37,2)
    s.rect("cream",76,12,8,5)
    s.line("night", (80,12),(80,6),weight=1)
    for x in range(51,113,10):
        s.rect("umber",x,42,2,13)
    s.rect("steel",28,58,107,3)


def flight(s):
    s.base("sky")
    s.ink("mist",((0,22),(28,18),(61,25),(108,12),(160,19),(160,38),(0,34)))
    s.rect("slate",0,52,160,12)
    for x in range(9,147,18):
        s.rect("cream",x,58,10,1.5)
    s.ink("white",((16,39),(47,39),(64,35),(88,20),(98,20),(90,34),
                   (130,27),(146,30),(138,35),(93,44),(81,50),(72,51),
                   (74,45),(28,46)))
    s.ink("brick",((27,40),(18,28),(27,27),(43,40),(73,39),(132,31),(137,34),(73,44),(28,45)))
    s.oval("night2",111,36,4,2)


def flood(s):
    s.base("steel")
    s.ink("pine",((0,49),(19,23),(48,35),(77,43),(101,27),(119,22),(159,43),(160,64),(0,64)))
    s.ink("ocean",((0,52),(35,44),(82,49),(124,44),(160,50),(160,64),(0,64)))
    s.rect("sand",100,32,22,16)
    s.ink("brick",((95,34),(111,23),(127,34)))
    s.rect("white",114,38,4,5)
    for x in range(7,157,12):
        s.line("sky",(x,8),(x-4,19),weight=.75)
    for x in (17,43,69,96,124):
        s.line("mist",(x,55),(x+17,54),weight=.75)


def poland(s):
    s.base("red75")
    s.ink("brick",((0,52),(79,31),(160,47),(160,64),(0,64)))
    s.ink("cream",((37,13),(88,9),(113,55),(51,62)))
    s.line("slate",(48,20),(88,17),weight=1.6)
    for row in range(5):
        s.line("umber",(51+2*row,25+5*row),(90+2*row,23+5*row),weight=.7)
    s.oval("night2",105,30,14,13)
    s.oval("sky",105,30,10,9)
    s.line("night2",(116,38),(132,53),weight=3.4)


SCENES = {
    "dymer": dymer, "summit": summit, "radar": radar, "factory": factory,
    "ship": ship, "ballot": ballot, "exam": exam, "racing": racing,
    "cricket": cricket, "boat": boat, "quake": quake, "capitol": capitol,
    "flight": flight, "flood": flood, "poland": poland,
}
