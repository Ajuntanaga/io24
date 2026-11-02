"""Silver dynamics faceplates and shared control geometry for the GTK Host.

Artwork is drawn from live values, never from a screenshot containing controls.
The 2156 x 482 bay is the same physical rectangle as all three EQ racks. Cairo
is loaded only by the renderer; parameter math remains usable without GTK.
"""
import math
import random
from dataclasses import dataclass, replace
from functools import lru_cache


WIDTH, HEIGHT = 2156, 482
INK = (0.105, 0.10, 0.09)
GREEN = (0.28, 0.90, 0.80)
AMBER = (1.0, 0.72, 0.32)
DIM = (0.48, 0.59, 0.55)


@dataclass(frozen=True)
class Parameter:
    key: str
    title: str
    low: float
    high: float
    default: float
    unit: str = "dB"
    logarithmic: bool = False
    off_at_minimum: bool = False

    def fraction(self, value):
        value = max(self.low, min(self.high, value))
        if self.logarithmic:
            return math.log(value / self.low) / math.log(self.high / self.low)
        return (value - self.low) / (self.high - self.low)

    def value(self, fraction):
        fraction = max(0.0, min(1.0, fraction))
        if self.logarithmic:
            return self.low * (self.high / self.low) ** fraction
        value = self.low + fraction * (self.high - self.low)
        return round(value) if self.unit == "choice" else value

    def text(self, value):
        if self.unit == "Hz":
            if self.off_at_minimum and value <= 41:
                return "OFF"
            return ("%.2f kHz" % (value / 1000) if value >= 1000
                    else "%.0f Hz" % value)
        if self.unit == "s":
            ms = value * 1000
            return ("%.2f" % ms if ms < 1 else "%.1f" % ms) + " ms"
        if self.unit == "ratio":
            return "%.1f:1" % value
        if self.unit == "choice":
            return ("4:1", "8:1", "12:1", "20:1", "ALL")[int(value)]
        if self.unit == "dB":
            return "%.1f dB" % value
        return "%.1f" % value

    def tick_text(self, fraction):
        value = self.value(fraction)
        if self.unit == "s":
            value *= 1000
        if self.unit == "choice":
            return self.text(value)
        if self.unit == "Hz" and value >= 1000:
            return "%gk" % round(value / 1000, 1)
        return "%g" % float("%.2g" % value)


GATE = (
    Parameter("gth", "THRESHOLD", -84, 0, -40),
    Parameter("grange", "RANGE", -84, 0, -60),
    Parameter("gatk", "ATTACK", .00002, .5, .005, "s", True),
    Parameter("grel", "RELEASE", .05, 2, .3, "s", True),
    Parameter("gkey", "KEY FILTER", 40, 16000, 40, "Hz", True, True),
)
STANDARD = (
    Parameter("cth", "THRESHOLD", -56, 0, 0),
    Parameter("rat", "RATIO", 1, 20, 2, "ratio", True),
    Parameter("catk", "ATTACK", .0002, .15, .02, "s", True),
    Parameter("crel", "RELEASE", .0025, .9, .15, "s", True),
    Parameter("mk", "GAIN", 0, 28, 0),
    Parameter("ckey", "KEY FILTER", 40, 16000, 40, "Hz", True, True),
)
TUBE = (
    Parameter("tpeak", "PEAK REDUCTION", 0, 100, 0, ""),
    Parameter("tgain", "GAIN", 0, 100, 40, ""),
    STANDARD[-1],
)
FET = (
    Parameter("finput", "INPUT", -56, 0, -43),
    Parameter("foutput", "OUTPUT", -56, 0, 0),
    Parameter("fatk", "ATTACK", .000021, .0008, .0001, "s", True),
    Parameter("frel", "RELEASE", .05, 1.1, .25, "s", True),
    Parameter("fratio", "RATIO", 0, 4, 0, "choice"),
    STANDARD[-1],
)


CROSSOVERS = (
    Parameter("x0", "LOW / LOW MID", 40, 400, 150, "Hz", True),
    Parameter("x1", "LOW MID / HIGH MID", 300, 2500, 800, "Hz", True),
    Parameter("x2", "HIGH MID / HIGH", 2000, 12000, 4500, "Hz", True),
)
BAND_NAMES = ("LOW", "LOW MID", "HIGH MID", "HIGH")
BAND_COLORS = (GREEN, (.63, .87, .49), AMBER, (.94, .48, .31))


def parameters(kind, model=0, band=0):
    if kind == "gate":
        return GATE
    specs = (STANDARD, TUBE, FET, CROSSOVERS)[model]
    if kind == "band":
        # Reset uses this band's canonical defaults, including its independent
        # detector frequency. 40 Hz is a frequency here, never an off sentinel.
        defaults = {
            "cth": (-18, -20, -20, -22)[band],
            "rat": (3, 2.5, 2.5, 3)[band],
            "catk": (.020, .012, .006, .003)[band],
            "crel": (.200, .150, .100, .080)[band],
            "ckey": (100, 400, 2000, 8000)[band],
        }
        return tuple(replace(s, default=defaults.get(s.key, s.default),
                             off_at_minimum=False) for s in specs)
    return specs


def controls(kind, model=0):
    """Logical rectangles used identically by painting and native hit targets."""
    specs = parameters(kind, model)
    result = {}
    left, right = (185, 965) if kind == "gate" else (180, 1040)
    if model in (1, 3) and kind != "gate":
        left, right = 245, 960
    for i, spec in enumerate(specs):
        cx = left + i * (right - left) / max(1, len(specs) - 1)
        result[spec.key] = (cx - 70, 150, 140, 224)
    if kind != "band":
        result["power"] = (1983, 167, 82, 158)
    if kind == "gate":
        result.update({"gate_mode": (1070, 153, 113, 49),
                       "expander": (1070, 214, 113, 49),
                       "gklisten": (1095, 324, 63, 63)})
    else:
        for i in range(3 if kind == "band" else 4):
            result["model_" + str(i)] = (131 + 154 * i, 402, 143, 45)
        if kind == "band":
            result["keyon"] = (619, 402, 151, 45)
            for i in range(4):
                result["band_" + str(i)] = (600 + 154 * i, 44, 143, 45)
        if model == 0:
            result["knee"] = (781, 402, 150, 45)
            result["auto"] = (942, 402, 126, 45)
        elif model == 1:
            result["climit"] = (781, 402, 150, 45)
        if model != 3:
            result["cklisten"] = (1079, 402, 150, 45)
    return result


def _color(cr, color, alpha=1):
    cr.set_source_rgba(*color, alpha)


def _rect(cr, x, y, w, h, radius=0):
    cr.new_path()
    if not radius:
        cr.rectangle(x, y, w, h)
        return
    r = min(radius, w / 2, h / 2)
    for cx, cy, start in ((x + w - r, y + r, -90),
                           (x + w - r, y + h - r, 0),
                           (x + r, y + h - r, 90), (x + r, y + r, 180)):
        cr.arc(cx, cy, r, math.radians(start), math.radians(start + 90))
    cr.close_path()


def _fill(cr, color, x, y, w, h, radius=0, alpha=1):
    _rect(cr, x, y, w, h, radius)
    _color(cr, color, alpha)
    cr.fill()


def _gradient(cr, x, y, w, h, stops, radius=0, horizontal=False):
    import cairo
    gradient = cairo.LinearGradient(x, y, x + w if horizontal else x,
                                    y if horizontal else y + h)
    for position, rgb in stops:
        gradient.add_color_stop_rgb(position, *rgb)
    _rect(cr, x, y, w, h, radius)
    cr.set_source(gradient)
    cr.fill()


@lru_cache(maxsize=1)
def _font_options():
    import cairo
    options = cairo.FontOptions()
    # RGB subpixel antialiasing is only correct for text drawn straight onto a
    # physical screen. Cached ARGB artwork must remain neutral when composited.
    options.set_antialias(cairo.ANTIALIAS_GRAY)
    options.set_hint_style(cairo.HINT_STYLE_FULL)
    options.set_hint_metrics(cairo.HINT_METRICS_ON)
    return options


def _text(cr, text, x, y, size=22, color=INK, centered=False,
          font="DejaVu Sans", bold=False):
    import cairo
    cr.set_font_options(_font_options())
    cr.select_font_face(font, cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    ext = cr.text_extents(str(text))
    _color(cr, color)
    cr.move_to(x - (ext.width / 2 + ext.x_bearing if centered else 0), y)
    cr.show_text(str(text))


def _line(cr, points, color, width=1, alpha=1):
    if not points:
        return
    cr.new_path()
    cr.move_to(*points[0])
    for p in points[1:]:
        cr.line_to(*p)
    _color(cr, color, alpha)
    cr.set_line_width(width)
    cr.stroke()


def _circle(cr, x, y, radius, color, alpha=1):
    cr.new_path()
    cr.arc(x, y, radius, 0, math.tau)
    _color(cr, color, alpha)
    cr.fill()


def _radial(cr, cx, cy, radius, stops, light=(-.3, -.45)):
    import cairo
    gradient = cairo.RadialGradient(cx + radius * light[0],
                                    cy + radius * light[1], 0, cx, cy, radius)
    for position, rgb in stops:
        gradient.add_color_stop_rgba(position, *rgb)
    cr.new_path()
    cr.arc(cx, cy, radius, 0, math.tau)
    cr.set_source(gradient)
    cr.fill()


@lru_cache(maxsize=1)
def _grain():
    """Fine anisotropic metal grain, shared by the plate and machined hardware."""
    from array import array
    import cairo
    rng = random.Random(2407)
    pixels = array("I")
    for _y in range(256):
        streak = rng.gauss(0, 7)
        row = rng.gauss(0, 3)
        for _x in range(512):
            streak = .94 * streak + rng.gauss(0, 2.8)
            v = int(max(0, min(255, 128 + streak + row + rng.gauss(0, 10))))
            pixels.append(0xff000000 | v << 16 | v << 8 | v)
    surface = cairo.ImageSurface.create_for_data(
        pixels, cairo.FORMAT_ARGB32, 512, 256, 512 * 4)
    pattern = cairo.SurfacePattern(surface)
    pattern.set_extend(cairo.EXTEND_REPEAT)
    return pattern


def _brush(cr, opacity=.7):
    import cairo
    cr.save()
    cr.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    cr.set_source(_grain())
    cr.paint_with_alpha(opacity)
    cr.restore()


def _engrave(cr, text, x, y, size=20, centered=False, bold=False,
             font="DejaVu Sans"):
    _text(cr, text, x, y + 1.1, size, (.95, .93, .87), centered, font, bold)
    _text(cr, text, x, y, size, INK, centered, font, bold)


def _screw(cr, x, y, angle):
    _radial(cr, x + 2, y + 4, 24,
            [(0, (0, 0, 0, .9)), (.66, (0, 0, 0, .5)), (1, (0, 0, 0, 0))])
    _radial(cr, x, y, 19,
            [(0, (.25, .24, .20, 1)), (.76, (.23, .22, .18, 1)),
             (.85, (.93, .91, .83, 1)), (.93, (.67, .65, .58, 1)),
             (1, (.18, .17, .14, 1))])
    _radial(cr, x, y, 15.2,
            [(0, (.35, .34, .29, 1)), (.65, (.14, .14, .12, 1)),
             (1, (.025, .026, .024, 1))])
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    for a in (0, math.pi / 2):
        cr.save()
        cr.rotate(a)
        _fill(cr, (.51, .49, .42), -9, -2.2, 18, 5.5, 1.5)
        _fill(cr, (.02, .022, .019), -9, -3.4, 18, 4.8, 1.5)
        cr.restore()
    cr.restore()


@lru_cache(maxsize=4)
def faceplate(kind):
    """Expensive grain, machining, and fixed hardware are painted only once."""
    import cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    cr = cairo.Context(surface)
    _fill(cr, (.018, .02, .019), 0, 0, WIDTH, HEIGHT, 9)
    # Separate, full-height rack ears and a rolled aluminium face.
    for x, w in ((2, 72), (78, 2000), (2082, 72)):
        _gradient(cr, x, 2, w, 476,
                  [(0, (.98, .96, .90)), (.006, (.82, .8, .73)),
                   (.014, (.37, .36, .31)), (.024, (.91, .89, .82)),
                   (.055, (.77, .75, .69)), (.25, (.73, .71, .65)),
                   (.55, (.78, .76, .70)), (.86, (.69, .67, .61)),
                   (.974, (.63, .61, .55)), (.985, (.91, .89, .82)),
                   (.996, (.24, .23, .20)), (1, (.10, .10, .09))], 7)
        _line(cr, [(x + 2, 12), (x + 2, 467)], (.98, .95, .87), 1.5, .9)
        _line(cr, [(x + w - 2, 12), (x + w - 2, 468)], (.1, .1, .085), 2, .7)
    rng = random.Random(1724)
    cr.save()
    _rect(cr, 5, 11, WIDTH - 10, HEIGHT - 24, 4)
    cr.clip()
    _brush(cr, .92)
    for _ in range(7900):
        x, y = rng.uniform(0, WIDTH), rng.uniform(9, 471)
        length = rng.uniform(3, 160)
        shade = (1, .98, .91) if rng.random() > .48 else (.13, .12, .10)
        _line(cr, [(x, y), (x + length * .6, y + .1),
                   (x + length, y + rng.uniform(-.35, .35))], shade,
              rng.uniform(.3, .85), rng.uniform(.045, .21))
    # Small, irregular machining pits prevent broad bands looking like a gradient.
    for _ in range(4800):
        x, y = rng.uniform(3, WIDTH - 3), rng.uniform(12, HEIGHT - 13)
        _line(cr, [(x, y), (x + rng.uniform(.4, 3), y)],
              (.18, .16, .12), rng.uniform(.35, .9), rng.uniform(.05, .17))
    cr.restore()
    for x in (75, 2079):
        _fill(cr, (.035, .036, .032), x, 7, 3, 465, 1)
    for x in (36, 2120):
        for y in (70, 408):
            _gradient(cr, x - 23, y - 15, 46, 30,
                      [(0, (.26, .25, .22)), (.45, (.68, .66, .59)),
                       (1, (.98, .95, .88))], 14)
            _gradient(cr, x - 21, y - 13, 42, 25,
                      [(0, (.015, .018, .016)), (1, (.12, .13, .11))], 12)
    for x in (104, 2053):
        for y in (35, 448):
            _screw(cr, x, y, .12 if y == 35 else -.22)
    if kind == "gate":
        _line(cr, [(1047, 123), (1047, 409)], (.21, .20, .18), 1.5, .8)
        _line(cr, [(1049, 123), (1049, 409)], (1, .97, .9), 1, .9)
    return surface


@lru_cache(maxsize=1)
def _dial_face():
    """A flat, lathe-finished cap with fixed illumination, cached for all knobs."""
    import cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 110, 110)
    cr = cairo.Context(surface)
    cx = cy = 55
    _radial(cr, cx, cy, 50,
            [(0, (.3, .29, .25, 1)), (.88, (.28, .27, .23, 1)),
             (.91, (.94, .92, .84, 1)), (.95, (.78, .76, .69, 1)),
             (1, (.11, .11, .09, 1))])
    cr.save()
    cr.arc(cx, cy, 46, 0, math.tau)
    cr.clip()
    _circle(cr, cx, cy, 46, (.64, .63, .58))
    # Anisotropic reflections describe a planar disc, with no central bump.
    for stroke in range(480):
        angle = stroke * math.tau / 480
        reflection = .5 + .5 * math.cos(2 * (angle + .65))
        shade = .46 + .47 * reflection
        cr.new_path()
        cr.move_to(cx, cy)
        cr.arc(cx, cy, 47, angle, angle + math.tau / 480 + .002)
        cr.close_path()
        _color(cr, (shade, shade * .99, shade * .94))
        cr.fill()
    _brush(cr, .52)
    for i in range(4, 87):
        cr.new_path()
        cr.arc(cx, cy, i * .53, 0, math.tau)
        _color(cr, (.16, .15, .12), .12 if i % 3 else .2)
        cr.set_line_width(.25 if i % 3 else .4)
        cr.stroke()
    cr.restore()
    return surface


def _readout(cr, cx, y, text):
    _gradient(cr, cx - 73, y, 146, 44,
              [(0, (.21, .21, .18)), (.15, (.49, .48, .42)),
               (.85, (.88, .86, .79)), (1, (.97, .95, .88))], 5)
    _fill(cr, (.018, .021, .017), cx - 71, y + 2, 142, 39, 4)
    _gradient(cr, cx - 68, y + 4, 136, 34,
              [(0, (.009, .014, .01)), (.32, (.039, .047, .032)),
               (1, (.013, .019, .014))], 3)
    _line(cr, [(cx - 66, y + 5), (cx + 66, y + 5)], (1, 1, .9), 1, .18)
    _text(cr, text, cx, y + 29, 23, (.99, .94, .68),
          centered=True, font="DejaVu Sans Mono")


def _knob(cr, spec, value, rect, focused=False, hovered=False, large=False):
    x, y, w, _h = rect
    cx, cy = x + w / 2, y + 95
    f = spec.fraction(value)
    _engrave(cr, spec.title, cx, y - (40 if large else 24), 20,
             centered=True, bold=True)
    # Even angular intervals match Parameter's linear/logarithmic mapping.
    # Dense six-knob bays use three labels so adjacent scales never collide.
    marked = (0, .25, .5, .75, 1) if large else (0, .5, 1)
    label_radius = 111 if large else 97
    for fraction in marked:
        angle = math.radians(135 + fraction * 270)
        _engrave(cr, spec.tick_text(fraction), cx + label_radius * math.cos(angle),
                 cy + label_radius * math.sin(angle) + 5, 16, centered=True)
    cr.save()
    if large:
        cr.translate(cx, cy)
        cr.scale(1.14, 1.14)
        cr.translate(-cx, -cy)
    for tick in range(33):
        angle = math.radians(135 + tick * 270 / 32)
        major = tick % 8 == 0
        r1, r2 = (74, 85) if major else (78, 84)
        points = [(cx + r1 * math.cos(angle), cy + r1 * math.sin(angle)),
                  (cx + r2 * math.cos(angle), cy + r2 * math.sin(angle))]
        _line(cr, [(px, py + .8) for px, py in points], (1, .97, .88), 1.7, .9)
        _line(cr, points, INK, 1.8 if major else 1.1, .95)
    # Contact occlusion and cast shadow belong to the plate, not the dial rotation.
    _radial(cr, cx + 5, cy + 13, 81,
            [(0, (0, 0, 0, .82)), (.63, (0, 0, 0, .62)),
             (.82, (0, 0, 0, .25)), (1, (0, 0, 0, 0))], (0, 0))
    _radial(cr, cx, cy + 4, 69,
            [(0, (.04, .043, .035, 1)), (.92, (.025, .028, .023, 1)),
             (.96, (.32, .32, .28, 1)), (1, (.05, .05, .04, 1))])
    _radial(cr, cx, cy, 65,
            [(0, (.14, .145, .125, 1)), (.7, (.12, .125, .11, 1)),
             (.92, (.07, .075, .062, 1)), (1, (.023, .027, .02, 1))])
    rotation = math.radians(135 + 270 * f)
    # Grooves really rotate; their illumination is fixed in room coordinates.
    for tooth in range(80):
        angle = tooth * math.tau / 80 + rotation
        light = .5 + .5 * math.cos(angle + 2.25)
        points = [(cx + r * math.cos(angle), cy + r * math.sin(angle))
                  for r in (52, 64)]
        _line(cr, points, (.018, .02, .016), 2.8, .85)
        edge = angle + .018
        _line(cr, [(cx + r * math.cos(edge), cy + r * math.sin(edge))
                   for r in (53, 63)], (.19, .195, .17), 1.2, .25 + .7 * light)
    cr.set_source_surface(_dial_face(), cx - 55, cy - 57)
    cr.paint()
    # Warm enamel in an engraved slot, extending into the rubber index ring.
    points = [(cx + r * math.cos(rotation), cy - 2 + r * math.sin(rotation))
              for r in (33, 58)]
    _line(cr, [(px + 1, py + 1) for px, py in points], (.91, .87, .72), 6, .65)
    _line(cr, points, (.09, .085, .06), 5.6)
    _line(cr, points, (.96, .72, .31), 3.2)
    cr.restore()
    _readout(cr, cx, y + 180, spec.text(value))
    if focused or hovered:
        cr.new_path()
        cr.arc(cx, cy, 89, 0, math.tau)
        _color(cr, (.28, .36, .29) if not focused else (.28, .19, .025),
               .5 if not focused else 1)
        cr.set_line_width(2 if not focused else 3)
        cr.stroke()


@lru_cache(maxsize=32)
def _knob_surface(spec, value, focused, hovered, large, raster_scale):
    """Reuse unchanged controls when another knob moves, at monitor resolution."""
    import cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 math.ceil(360 * raster_scale),
                                 math.ceil(310 * raster_scale))
    surface.set_device_scale(raster_scale, raster_scale)
    _knob(cairo.Context(surface), spec, value, (110, 70, 140, 224),
          focused, hovered, large)
    return surface


def _cached_knob(cr, spec, value, rect, focused, hovered, large,
                 raster_scale):
    surface = _knob_surface(spec, value, focused, hovered, large, raster_scale)
    # Padding includes the title, engraved scale and cast shadow.
    # Place the native-resolution cache on whole device pixels so Cairo does
    # not blur its lettering and grip texture through another bilinear pass.
    x = round((rect[0] + rect[2] / 2 - 180) * raster_scale) / raster_scale
    y = round((rect[1] - 70) * raster_scale) / raster_scale
    cr.set_source_surface(surface, x, y)
    cr.paint()


def _jewel(cr, cx, cy, radius, on):
    _radial(cr, cx + 1, cy + 2, radius + 5,
            [(0, (0, 0, 0, .65)), (.7, (0, 0, 0, .4)), (1, (0, 0, 0, 0))])
    _radial(cr, cx, cy, radius + 3,
            [(0, (.10, .10, .08, 1)), (.76, (.11, .11, .08, 1)),
             (.82, (.9, .86, .72, 1)), (.92, (.42, .40, .31, 1)),
             (1, (.09, .09, .06, 1))])
    if on:
        _radial(cr, cx, cy, radius * 2.6,
                [(0, (1, .61, .12, .28)), (.45, (1, .56, .10, .12)),
                 (1, (1, .55, .08, 0))], (0, 0))
    _radial(cr, cx, cy, radius,
            [(0, (1, .97, .67, 1) if on else (.24, .23, .16, 1)),
             (.45, (1, .79, .29, 1) if on else (.17, .16, .10, 1)),
             (.82, (.98, .52, .06, 1) if on else (.09, .085, .055, 1)),
             (1, (.42, .21, .02, 1) if on else (.035, .034, .022, 1))])
    _circle(cr, cx - radius * .25, cy - radius * .3, radius * .25,
            (1, .98, .83), .8 if on else .15)


def _button(cr, rect, name, active, focused=False, indicator=False):
    x, y, w, h = rect
    # A narrow metal mounting rim, black gasket, and raised phenolic key cap.
    _gradient(cr, x - 2, y - 2, w + 4, h + 5,
              [(0, (.24, .23, .20)), (.06, (.12, .12, .10)),
               (.8, (.59, .57, .50)), (1, (.96, .93, .85))], 5)
    _fill(cr, (.025, .028, .023), x, y, w, h, 4)
    _gradient(cr, x + 4, y + 3, w - 8, h - 8,
              [(0, (.32, .33, .28)), (.08, (.18, .19, .16)),
               (.32, (.115, .125, .102)), (1, (.065, .075, .06))], 3)
    _line(cr, [(x + 7, y + h - 7), (x + w - 7, y + h - 7)], (0, 0, 0), 1.5, .9)
    if indicator:
        _jewel(cr, x + (w / 2 - 12 if name == "" else 24), y + h / 2 - 1, 10, active)
        if name:
            words = name.split()
            for i, line in enumerate(words):
                _text(cr, line, x + (w + 34) / 2,
                      y + h / 2 + 6 + (i - (len(words) - 1) / 2) * 17,
                      16, (.9, .89, .81), centered=True)
        else:
            _fill(cr, (.07, .08, .065), x + w - 30, y + 17, 12, 13, 2)
    else:
        if active:
            _gradient(cr, x + 6, y + 5, w - 12, h - 13,
                      [(0, (.79, .47, .16)), (.12, (1, .91, .65)),
                       (.4, (1, .76, .33)), (.9, (.95, .65, .25)),
                       (1, (.54, .29, .08))], 2)
            _line(cr, [(x + 9, y + 7), (x + w - 9, y + 7)], (1, .97, .81), 1.5, .9)
        _text(cr, name, x + w / 2, y + h / 2 + 6, 17,
              (.22, .12, .045) if active else (.86, .85, .78), centered=True, bold=active)
    if focused:
        _rect(cr, x - 5, y - 5, w + 10, h + 10, 7)
        _color(cr, (.28, .19, .025))
        cr.set_line_width(3)
        cr.stroke()


def _listen_button(cr, rect, name, active, focused=False):
    """A latching, prismatic amber key in a deep black and nickel housing."""
    x, y, w, h = rect
    side = h if not name else h - 2
    bx, by = (x, y) if not name else (x + 1, y + 1)
    if name:
        _gradient(cr, x - 2, y - 2, w + 4, h + 5,
                  [(0, (.18, .18, .15)), (.86, (.47, .46, .40)),
                   (1, (.96, .93, .84))], 5)
        _gradient(cr, x, y, w, h,
                  [(0, (.12, .13, .105)), (1, (.045, .052, .039))], 4)
    _fill(cr, (0, 0, 0), bx + 2, by + 4, side, side, 6, .35)
    _gradient(cr, bx - 1, by - 1, side + 2, side + 2,
              [(0, (.96, .94, .84)), (.04, (.48, .48, .40)),
               (.16, (.10, .11, .085)), (.86, (.055, .063, .048)),
               (.96, (.63, .62, .53)), (1, (.91, .88, .79))], 5)
    _gradient(cr, bx + 3, by + 3, side - 6, side - 6,
              [(0, (.018, .022, .014)), (.65, (.075, .08, .057)),
               (1, (.27, .27, .19))], 3)
    inset = 9 if not name else 7
    lx, ly, size = bx + inset, by + inset, side - 2 * inset
    _gradient(cr, lx - 2, ly - 2, size + 4, size + 4,
              [(0, (.08, .046, .012)), (.3, (.32, .22, .08)),
               (1, (.68, .52, .25))], 3)
    _gradient(cr, lx, ly, size, size,
              ([(0, (.99, .67, .19)), (.12, (1, .91, .51)),
                (.5, (1, .73, .27)), (.9, (.93, .48, .075)),
                (1, (.56, .24, .027))] if active else
               [(0, (.31, .26, .16)), (.15, (.25, .22, .13)),
                (.6, (.14, .13, .074)), (1, (.075, .071, .036))]), 2)
    cr.save()
    _rect(cr, lx + 1, ly + 1, size - 2, size - 2, 2)
    cr.clip()
    if active:
        _radial(cr, lx + size * .45, ly + size * .42, size * .7,
                [(0, (1, .99, .79, .95)), (.4, (1, .9, .43, .62)),
                 (1, (1, .65, .08, 0))])
    # Fine moulded prisms diffuse the lamp, rather than a flat coloured square.
    for i in range(2, int(size), 3):
        _line(cr, [(lx + i, ly), (lx + i, ly + size)], (1, .92, .58),
              .65, .24 if active else .08)
        _line(cr, [(lx, ly + i), (lx + size, ly + i)], (.36, .16, .025),
              .5, .17 if active else .13)
    _line(cr, [(lx + 2, ly + size - 4), (lx + 2, ly + 2),
               (lx + size - 3, ly + 2)], (1, .98, .81), 1.1, .9 if active else .25)
    cr.restore()
    if active:
        _radial(cr, bx + side / 2, by + side / 2, side * .86,
                [(0, (1, .64, .12, 0)), (.48, (1, .6, .08, .09)),
                 (1, (1, .55, .06, 0))], (0, 0))
    if name:
        for i, word in enumerate(name.split()):
            _text(cr, word, x + side + (w - side) / 2, y + h / 2 - 3 + 17 * i,
                  16, (.97, .91, .72) if active else (.85, .85, .76), centered=True)
    if focused:
        _rect(cr, x - 5, y - 5, w + 10, h + 10, 7)
        _color(cr, (.28, .19, .025))
        cr.set_line_width(3)
        cr.stroke()


def _power(cr, rect, on, focused):
    x, y, w, h = rect
    cx, cy = x + w / 2, y + h / 2 - 8
    _engrave(cr, "POWER", cx, y - 53, 20, centered=True, bold=True)
    _engrave(cr, "ON", cx, y - 20, 20, centered=True)
    _radial(cr, cx + 6, cy + 9, 48,
            [(0, (0, 0, 0, .9)), (.64, (0, 0, 0, .58)), (1, (0, 0, 0, 0))])
    # Bright lathed washer beneath a bevelled hex nut: each facet catches light
    # independently, leaving a real dark recess around the ball joint.
    _radial(cr, cx, cy, 39,
            [(0, (.25, .26, .23, 1)), (.77, (.34, .35, .30, 1)),
             (.82, (.98, .97, .9, 1)), (.87, (.52, .54, .48, 1)),
             (.94, (.85, .87, .80, 1)), (1, (.12, .14, .11, 1))])
    outer = [(cx + 35 * math.cos(i * math.tau / 6),
              cy + 35 * math.sin(i * math.tau / 6)) for i in range(6)]
    inner = [(cx + 28 * math.cos(i * math.tau / 6),
              cy + 28 * math.sin(i * math.tau / 6)) for i in range(6)]
    cr.save()
    cr.new_path()
    cr.move_to(*outer[0])
    for point in outer[1:]:
        cr.line_to(*point)
    cr.close_path()
    cr.clip()
    _gradient(cr, cx - 35, cy - 35, 70, 70,
              [(0, (.96, .98, .94)), (.2, (.67, .71, .66)),
               (.45, (.87, .89, .84)), (.52, (.25, .29, .25)),
               (.76, (.62, .65, .59)), (1, (.17, .20, .17))], horizontal=True)
    _brush(cr, .75)
    for i, shade in enumerate((.32, .17, .46, .93, .97, .65)):
        j = (i + 1) % 6
        cr.new_path()
        cr.move_to(*outer[i])
        for point in (outer[j], inner[j], inner[i]):
            cr.line_to(*point)
        cr.close_path()
        _color(cr, (shade, shade, shade * .95))
        cr.fill()
        _line(cr, [inner[i], inner[j]], (.99, .99, .92), .8, .65)
    cr.restore()
    _radial(cr, cx, cy, 23,
            [(0, (.025, .031, .025, 1)), (.76, (.035, .045, .035, 1)),
             (.84, (.11, .13, .10, 1)), (.9, (.8, .83, .75, 1)),
             (1, (.12, .15, .11, 1))])
    _radial(cr, cx - 1, cy - 1, 18,
            [(0, (.89, .93, .88, 1)), (.4, (.5, .57, .5, 1)),
             (.67, (.17, .21, .17, 1)), (1, (.028, .035, .027, 1))])
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(math.radians(9 if on else 171))
    _line(cr, [(7, 4), (10, -54)], (0, 0, 0), 31, .45)
    _gradient(cr, -8, -34, 16, 41,
              [(0, (.12, .16, .13)), (.18, (.82, .87, .82)),
               (.31, (1, 1, .96)), (.45, (.56, .65, .59)),
               (.72, (.16, .21, .17)), (1, (.53, .59, .52))], 6, horizontal=True)
    for yy in range(-24, 0, 3):
        _line(cr, [(-6, yy), (6, yy + .8)], (.09, .13, .10), .8, .75)
        _line(cr, [(-6, yy + 1), (5, yy + 1.7)], (.86, .9, .8), .6, .6)
    _gradient(cr, -15, -69, 30, 50,
              [(0, (.13, .18, .15)), (.09, (.5, .58, .52)),
               (.23, (.98, 1, .98)), (.36, (.89, .95, .90)),
               (.46, (.45, .55, .49)), (.64, (.14, .21, .17)),
               (.79, (.31, .39, .32)), (.94, (.68, .75, .65)),
               (1, (.16, .22, .17))], 13, horizontal=True)
    cr.save()
    _rect(cr, -14, -66, 28, 44, 11)
    cr.clip()
    _brush(cr, .5)
    for yy in range(-60, -23, 2):
        _line(cr, [(-12, yy), (12, yy + .4)], (.94, .98, .90), .35, .18)
    cr.restore()
    _line(cr, [(-10, -57), (-10, -29)], (1, 1, .97), 1.1, .95)
    _line(cr, [(11, -56), (11, -27)], (.03, .07, .04), .9, .8)
    cr.save()
    cr.translate(0, -63)
    cr.scale(1, .61)
    _radial(cr, 0, 0, 13.5,
            [(0, (1, 1, .98, 1)), (.52, (.90, .94, .89, 1)),
             (.84, (.57, .65, .58, 1)), (.93, (.93, .96, .87, 1)),
             (1, (.18, .25, .19, 1))])
    cr.restore()
    cr.restore()
    _jewel(cr, cx, y + h + 25, 15, on)
    if focused:
        _rect(cr, x - 3, y - 5, w + 6, h + 10, 8)
        _color(cr, (.28, .19, .025))
        cr.set_line_width(3)
        cr.stroke()


def _screen(cr, kind, meters=True):
    x = 1222 if kind == "gate" else 1264
    y, w, h = 42, 1960 - x, 396
    # Milled opening: bright lower lip, shaded upper cut, gasket, then inset glass.
    _gradient(cr, x - 14, y - 14, w + 28, h + 29,
              [(0, (.19, .19, .16)), (.025, (.47, .46, .40)),
               (.06, (.15, .16, .13)), (.89, (.35, .35, .29)),
               (.97, (.96, .94, .86)), (1, (.67, .65, .57))], 13)
    _gradient(cr, x - 10, y - 10, w + 20, h + 20,
              [(0, (.61, .60, .53)), (.025, (.2, .21, .18)),
               (.08, (.07, .08, .065)), (.94, (.1, .12, .093)),
               (1, (.4, .42, .35))], 10)
    _fill(cr, (.008, .014, .009), x - 4, y - 4, w + 8, h + 8, 8)
    _gradient(cr, x, y, w, h,
              [(0, (.012, .026, .017)), (.25, (.018, .038, .023)),
               (.68, (.025, .043, .026)), (1, (.008, .018, .011))], 6)
    _line(cr, [(x + 9, y + h + 1), (x + w - 9, y + h + 1)], (.66, .7, .57), 1, .5)
    if meters:
        _gradient(cr, x + w - 120, y + 5, 114, h - 10,
                  [(0, (.026, .034, .024)), (.5, (.012, .022, .014)),
                   (1, (.007, .014, .009))], 5)
        _line(cr, [(x + w - 123, y + 10), (x + w - 123, y + h - 10)], (.3, .36, .28), 1, .5)
    return x, y, w, h


def _grid(cr, rect, low=-84, high=0, ticks=(0, -20, -40, -60, -80),
          right_axis=False):
    x, y, w, h = rect
    _fill(cr, (.005, .017, .009), x, y, w, h, 0, .45)
    for i in range(13):
        px = x + w * i / 12
        _line(cr, [(px, y), (px, y + h)], (.45, .66, .47),
              .8, .23 if i % 3 == 0 else .12)
    for value in ticks:
        yy = y + h * (high - value) / (high - low)
        _line(cr, [(x, yy), (x + w, yy)], (.48, .68, .49), .8, .27)
        _text(cr, str(value), x + w + 20 if right_axis else x - 21,
              yy + 5, 14, (.65, .73, .62), centered=True)
    _rect(cr, x, y, w, h)
    _color(cr, (.52, .65, .48), .42)
    cr.set_line_width(.9)
    cr.stroke()


def _history_axis(cr, x, y, w):
    for i in range(7):
        xx = x + i * w / 6
        _line(cr, [(xx, y), (xx, y + 4)], DIM, .8, .6)
    _text(cr, "EARLIER", x, y + 22, 14, DIM)
    _text(cr, "NOW", x + w - 35, y + 22, 14, DIM)


@lru_cache(maxsize=24)
def _weave_geometry(rows, samples, columns):
    """Fixed material coordinates: only the measured envelope changes per frame."""
    def point(u, v):
        interior = math.sin(math.pi * v)
        return (u, v, interior * 5 * math.sin(u * math.tau * 7 + v * math.tau * 1.7),
                interior * math.sin(u * math.tau * 13 - v * math.tau * 2.2))
    contours = tuple(tuple(point(i / (samples - 1), row / rows)
                           for i in range(samples)) for row in range(1, rows))
    strands = tuple(tuple(point(column / columns, row / (rows * 2))
                          for row in range(rows * 2 + 1))
                    for column in range(columns + 1))
    return contours, strands


def _signal_fill(cr, points, baseline, rect, color):
    """Woven phosphor surface clipped beneath the unchanged measured outline.

    The mesh bends with the data; its interior threads are a material texture,
    not additional signals. No clock or fabricated telemetry drives the fill.
    """
    import cairo
    x, y, w, h = rect
    if len(points) < 2 or points[-1][0] <= points[0][0]:
        return
    matrix = cr.get_matrix()
    raster_scale = math.hypot(matrix.xx, matrix.yx) * cr.get_target().get_device_scale()[0]
    cr.save()
    cr.rectangle(x, y, w, h)
    cr.clip()
    # Compose the material once, then apply the curved envelope once. Clipping
    # every fine stroke to that envelope repeatedly rasterizes its alpha mask.
    cr.push_group()
    gradient = cairo.LinearGradient(0, baseline, 0, y + h if baseline == y else y)
    gradient.add_color_stop_rgba(0, *color, .045)
    gradient.add_color_stop_rgba(.45, *color, .13)
    gradient.add_color_stop_rgba(1, *color, .27)
    cr.set_source(gradient)
    cr.paint()
    left, span = points[0][0], points[-1][0] - points[0][0]
    # Keep the material's thread spacing legible at the actual device resolution,
    # without tessellating invisible detail on smaller racks. The signal outline
    # and clipping polygon still retain every measured sample.
    rows = max(6, min(18, int(h * raster_scale / 8)))
    samples = min(73, len(points), max(17, int(span * raster_scale / 5) + 1))
    columns = max(8, min(56, int(span * raster_scale / 9)))
    contours, strands = _weave_geometry(rows, samples, columns)
    depths = {}
    last = len(points) - 1
    for count in (samples - 1, columns):
        for i in range(count + 1):
            u = i / count
            sample = u * last
            index = min(last - 1, int(sample))
            fraction = sample - index
            depth = points[index][1] * (1 - fraction) + points[index + 1][1] * fraction - baseline
            depths[u] = (depth, min(5, abs(depth) * .07))

    def thread_points(thread):
        return [(left + span * u + dx,
                 baseline + depths[u][0] * v + depths[u][1] * dy)
                for u, v, dx, dy in thread]

    # Closely spaced contour threads become a fluid surface as the envelope moves.
    for row, coordinates in enumerate(contours, 1):
        v = row / rows
        _line(cr, thread_points(coordinates), color, .9 if row % 4 else 1.2, .19 + .29 * v)
    # Cross-strands bow into the contours, producing a woven, liquid mesh rather
    # than the old flat translucent area or a second grid of vertical bars.
    highlight = tuple(min(1, c * .7 + .3) for c in color)
    threads = [thread_points(coordinates) for coordinates in strands]
    # Rasterize equal-material strands together. Stroking every strand separately
    # repeatedly composites the same clipped area during a crossover drag.
    for ink, width, alpha, group in (
            (color, .75, .26, [t for i, t in enumerate(threads) if i % 4]),
            (color, .75, .42, [t for i, t in enumerate(threads) if not i % 4]),
            (highlight, .8, .26, [t[-12:] for i, t in enumerate(threads) if not i % 5])):
        cr.new_path()
        for thread in group:
            cr.move_to(*thread[0])
            for point in thread[1:]:
                cr.line_to(*point)
        _color(cr, ink, alpha)
        cr.set_line_width(width)
        cr.stroke()
    material = cr.pop_group()
    cr.new_path()
    cr.move_to(points[0][0], baseline)
    for point in points:
        cr.line_to(*point)
    cr.line_to(points[-1][0], baseline)
    cr.close_path()
    cr.clip()
    cr.set_source(material)
    cr.paint()
    cr.restore()


@lru_cache(maxsize=16)
def _signal_surface(points, baseline, rect, color, raster_scale):
    """Bounded cache for parameter-driven plots; never used for live history."""
    import cairo
    x, y, w, h = rect
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 math.ceil(w * raster_scale),
                                 math.ceil(h * raster_scale))
    surface.set_device_scale(raster_scale, raster_scale)
    context = cairo.Context(surface)
    context.translate(-x, -y)
    _signal_fill(context, points, baseline, rect, color)
    return surface


def _static_signal_fill(cr, points, baseline, rect, color):
    matrix = cr.get_matrix()
    raster_scale = math.hypot(matrix.xx, matrix.yx) * cr.get_target().get_device_scale()[0]
    surface = _signal_surface(tuple(points), baseline, rect, color, raster_scale)
    cr.save()
    cr.set_source_surface(surface, rect[0], rect[1])
    cr.paint()
    cr.restore()


def _trace(cr, values, rect, color, low=-84, high=0, fill=False):
    x, y, w, h = rect
    if not values:
        return
    # The rolling window stays fixed when history is only partially populated.
    samples = values[-150:]
    start = x + w * (150 - len(samples)) / 149
    points = [(start + i * w / 149,
               y + h * (1 - max(0, min(1, (v - low) / (high - low)))))
              for i, v in enumerate(samples)]
    cr.save()
    cr.rectangle(x, y - 2, w, h + 4)
    cr.clip()
    if fill and len(points) > 1:
        baseline = y if fill == "top" else y + h
        _signal_fill(cr, points, baseline, rect, color)
    for thickness, alpha in ((10, .025), (5, .08), (2.1, .95), (.7, .48)):
        _line(cr, points, color, thickness, alpha)
    cr.restore()


def _meter(cr, x, y, h, value, title, color, reduction=False, available=True):
    _text(cr, title, x + 10, y - 22, 18, (.87, .89, .76), centered=True)
    _fill(cr, (.16, .20, .14), x - 6, y - 6, 32, h + 12, 3)
    _fill(cr, (.002, .008, .003), x - 4, y - 4, 28, h + 8, 2)
    amount = max(0, min(1, -value / 60 if reduction else (value + 60) / 60))
    for i in range(48):
        lit = available and i / 48 < amount
        yy = y + i * h / 48 if reduction else y + h - (i + 1) * h / 48
        # The input meter has a calibrated amber peak region, like the reference.
        segment = AMBER if not reduction and i >= 38 else color
        _fill(cr, segment, x, yy, 20, max(1, h / 48 - 1.7), 0, .95 if lit else .09)
        if lit:
            _fill(cr, (1, 1, .8), x + 1, yy, 18, .7, 0, .32)
    _text(cr, ("%.0f" % value) if available else "—", x + 10, y + h + 32,
          19, color, centered=True, font="DejaVu Sans Mono")


def _display_badge(cr, x, y, w, name, active=False):
    _gradient(cr, x, y, w, 31,
              [(0, (.25, .28, .21)), (.08, (.07, .09, .062)),
               (1, (.025, .038, .023))], 3)
    if active:
        _gradient(cr, x + 3, y + 3, w - 6, 25,
                  [(0, (.95, .67, .29)), (.3, (1, .84, .43)),
                   (1, (.7, .42, .13))], 2)
    _text(cr, name, x + w / 2, y + 21, 16,
          (.15, .1, .04) if active else (.69, .74, .62), centered=True, bold=active)


def transfer_output(level, threshold, ratio, makeup, knee=0.01, on=True):
    """Static RMS transfer, including the Host processor's exact knee law.

    This is the steady-state curve, not an inferred realtime reduction meter.
    Knee is the half-width stored in cpxt (io24_uc_comp.c:knee_reduction).
    """
    if not on:
        return level
    over = level - threshold
    slope = 1 - 1 / max(1, ratio)
    if knee <= .011:
        reduction = slope * max(0, over)
    elif over <= -knee:
        reduction = 0
    elif over >= knee:
        reduction = slope * over
    else:
        reduction = slope * (over + knee) ** 2 / (4 * knee)
    return level - reduction + makeup


def crossover_response(frequency, splits, sample_rate=48000):
    """Magnitudes of the actual, bilinear LR4 crossover legs.

    Each LP/HP leg has two Butterworth sections. The compensating allpasses
    have unit magnitude; the two upper bands also pass both earlier HP legs.
    """
    warped = math.tan(math.pi * frequency / sample_rate)
    low = [1 / (1 + (warped / math.tan(math.pi * f / sample_rate)) ** 4)
           for f in splits]
    high = [1 - value for value in low]
    return (low[0], high[0] * low[1], high[0] * high[1] * low[2],
            high[0] * high[1] * high[2])


def _frequency_grid(cr, rect, low=-48):
    x, y, w, h = rect
    _grid(cr, rect, low, 0, (0, low / 2, low))
    for freq, label in ((20, "20"), (100, "100"), (1000, "1k"),
                        (10000, "10k"), (20000, "20k")):
        xx = x + math.log(freq / 20) / math.log(1000) * w
        _line(cr, [(xx, y), (xx, y + h)], GREEN, .8, .15)
        # The small detector plot cannot fit both end labels 0.3 decades apart.
        if freq != 10000 or w >= 300:
            _text(cr, label, xx, y + h + 21, 14, DIM, centered=True)


def _glass(cr, x, y, w, h):
    cr.save()
    _rect(cr, x + 2, y + 2, w - 4, h - 4, 5)
    cr.clip()
    cr.new_path()
    cr.move_to(x, y)
    cr.line_to(x + w * .69, y)
    cr.line_to(x + w * .36, y + h)
    cr.line_to(x, y + h)
    cr.close_path()
    _color(cr, (.77, .9, .70), .018)
    cr.fill()
    for gy in range(int(y + 3), int(y + h), 4):
        _line(cr, [(x + 3, gy), (x + w - 3, gy)], (0, 0, 0), .5, .09)
    cr.restore()


def _crossover_display(cr, values, details):
    """Parameter-driven artwork; the measured input is painted separately."""
    x, y, w, h = _screen(cr, "comp")
    px, pw = x + 49, w - 204
    rect = (px, y + 76, pw, 162)
    _frequency_grid(cr, rect)
    for index, name in enumerate(BAND_NAMES):
        _line(cr, [(px + index * 125, y + 29), (px + index * 125 + 15, y + 29)],
              BAND_COLORS[index], 2.6)
        _text(cr, name, px + index * 125 + 23, y + 34, 15,
              BAND_COLORS[index], bold=True)
    splits = tuple(values["x%d" % i] for i in range(3))
    responses = [crossover_response(20 * 1000 ** (i / 160), splits,
                                    details.get("sample_rate", 48000))
                 for i in range(161)]
    for band, color in enumerate(BAND_COLORS):
        points = [(px + i * pw / 160,
                   rect[1] + rect[3] * min(1, -20 * math.log10(max(1e-9, r[band])) / 48))
                  for i, r in enumerate(responses)]
        _static_signal_fill(cr, points, rect[1] + rect[3], rect, color)
        _line(cr, points, color, 7, .05)
        _line(cr, points, color, 1.8, .94)
    for freq in splits:
        xx = px + math.log(freq / 20) / math.log(1000) * pw
        cr.set_dash([3, 5])
        _line(cr, [(xx, rect[1]), (xx, rect[1] + rect[3])], (.9, .92, .79), 1, .6)
        cr.set_dash([])
        _circle(cr, xx, rect[1] - 6, 3, (.9, .92, .79))
    _text(cr, "LR4 · CROSSOVER RESPONSE · Hz", px, y + 57, 14, DIM)
    _text(cr, "INPUT", px, y + 292, 16, GREEN)
    input_rect = (px, y + 307, pw, 49)
    _grid(cr, input_rect, -60, 0, (0, -60))
    _history_axis(cr, px, y + 359, pw)
    for db in (0, -12, -24, -36, -48, -60):
        _text(cr, str(db), x + w - 30, y + 80 - db / 60 * 260, 13, DIM,
              centered=True)


def _crossover_live(cr, history, online):
    x, y, w, h = 1264, 42, 696, 396
    px, pw = x + 49, w - 204
    live = list(history) if online else []
    _trace(cr, [r[0] for r in live], (px, y + 307, pw, 49),
           GREEN, low=-60, fill=True)
    if not live:
        _text(cr, "NO INPUT DATA", px + pw / 2, y + 337, 16, DIM, centered=True)
    _meter(cr, x + w - 70, y + 76, 260, live[-1][0] if live else -84,
           "IN", GREEN, available=bool(live))
    _glass(cr, x, y, w, h)


def _band_display(cr, values, states, transfer, details):
    x, y, w, h = _screen(cr, "band", meters=False)
    band = states.get("band", 0)
    color = BAND_COLORS[band]
    common = details["common"]
    _text(cr, BAND_NAMES[band] + " · STATIC TRANSFER", x + 39, y + 35,
          18, color, bold=True)
    tx, ty, tw, th = x + 49, y + 76, 307, 260
    rect = (tx, ty, tw, th)
    _grid(cr, rect, -60, 0, (0, -20, -40, -60))
    for db in (-60, -40, -20, 0):
        _text(cr, str(db), tx + (db + 60) / 60 * tw, ty + th + 23,
              14, DIM, centered=True)
    cr.set_dash([5, 5])
    _line(cr, [(tx, ty + th), (tx + tw, ty)], (.74, .77, .62), 1, .65)
    cr.set_dash([])
    threshold, ratio, makeup = transfer
    curve = []
    for i in range(161):
        output = transfer_output(-60 + i * 60 / 160, threshold, ratio, makeup,
                                 common["Knee width (dB)"], states["power"])
        curve.append((tx + i * tw / 160,
                      ty + th * (1 - (max(-60, min(0, output)) + 60) / 60)))
    _static_signal_fill(cr, curve, ty + th, rect, color)
    _line(cr, curve, color, 8, .07)
    _line(cr, curve, color, 2.3)
    _text(cr, "INPUT / OUTPUT · dB", tx + tw / 2, y + 383,
          14, DIM, centered=True)
    rx, rw = x + 421, 231
    _text(cr, "KEY FILTER", rx, y + 35, 17, GREEN, bold=True)
    key_rect = (rx, y + 76, rw, 100)
    _frequency_grid(cr, key_rect, -24)
    curve = []
    fs = details.get("sample_rate", 48000)
    for i in range(101):
        freq = 20 * 1000 ** (i / 100)
        angle = -math.tau * min(freq, fs * .49) / fs
        z = complex(math.cos(angle), math.sin(angle))
        numerator = common["Biquad b0"] + common["Biquad b1"] * z + common["Biquad b2"] * z * z
        denominator = 1 - common["Biquad -a1"] * z - common["Biquad -a2"] * z * z
        magnitude = abs(numerator / denominator) if abs(denominator) > 1e-12 else 1
        db = max(-24, min(0, 20 * math.log10(max(1e-9, magnitude))))
        curve.append((rx + i * rw / 100, key_rect[1] - db / 24 * key_rect[3]))
    _static_signal_fill(cr, curve, key_rect[1] + key_rect[3], key_rect, GREEN)
    _line(cr, curve, GREEN, 1.8)
    _text(cr, "ENABLED" if states["keyon"] else "BYPASSED", rx, y + 230,
          15, GREEN if states["keyon"] else DIM)
    _text(cr, "LISTEN" if states["cklisten"] else "DETECTOR", rx + rw - 40, y + 230,
          15, AMBER if states["cklisten"] else DIM, centered=True)
    for index, (name, value) in enumerate((
            ("ATTACK", "%.2f ms" % (common["Attack time (s)"] * 1000)),
            ("RELEASE", "%.1f ms" % (common["Release time (s)"] * 1000)),
            ("RATIO", "LIMIT" if ratio >= 1000 else "%.1f:1" % ratio))):
        yy = y + 273 + index * 33
        _text(cr, name, rx, yy, 14, DIM)
        _text(cr, value, rx + 127, yy, 16, color, font="DejaVu Sans Mono")
    _text(cr, "STEADY-STATE RESPONSE", rx, y + 383, 13, DIM)
    _glass(cr, x, y, w, h)


def _display(cr, kind, model, values, history, online, on, transfer, details):
    if model == 3:
        _crossover_live(cr, history, online)
        return
    x, y, w, h = _screen(cr, kind)
    # Telemetry has input and separate gate/compressor gain reduction. No output
    # stream is invented to copy the reference's otherwise similar second meter.
    source = list(history) if online else []
    inputs = [frame[0] for frame in source]
    gains = [frame[1] for frame in source]
    last_in = inputs[-1] if inputs else -84
    last_gr = gains[-1] if gains else 0
    meter_y, meter_h = y + 76, 260
    _meter(cr, x + w - 104, meter_y, meter_h, last_in, "IN", GREEN, available=online)
    _meter(cr, x + w - 36, meter_y, meter_h, last_gr, "GR", AMBER,
           reduction=True, available=online and (kind == "gate" or model != 3))
    for db in (0, -12, -24, -36, -48, -60):
        _text(cr, str(db), x + w - 60, meter_y - db / 60 * meter_h + 4,
              13, (.65, .69, .56), centered=True)
    if kind == "gate":
        px, pw = x + 51, w - 205
        _line(cr, [(px, y + 28), (px + 28, y + 28)], GREEN, 2.3)
        _text(cr, "INPUT", px + 38, y + 34, 18, (.87, .91, .77))
        cr.set_dash([6, 4])
        _line(cr, [(px + 169, y + 28), (px + 196, y + 28)], AMBER, 2)
        cr.set_dash([])
        _text(cr, "THRESHOLD", px + 207, y + 34, 17, (.87, .87, .71))
        rect = (px, y + 66, pw, 175)
        _grid(cr, rect)
        _trace(cr, inputs, rect, GREEN, fill=True)
        threshold = max(-84, min(0, values["gth"]))
        ty = rect[1] - threshold / 84 * rect[3]
        cr.set_dash([7, 5])
        _line(cr, [(px, ty), (px + pw, ty)], AMBER, 1.7, .95)
        cr.set_dash([])
        _fill(cr, (.028, .034, .017), px + pw - 69, ty - 20, 67, 19, 2, .9)
        _text(cr, "%g dB" % threshold, px + pw - 34, ty - 6,
              14, AMBER, centered=True)
        _fill(cr, AMBER, px, y + 261, 28, 10, 0, .25)
        _line(cr, [(px, y + 261), (px + 28, y + 261)], AMBER, 1)
        _text(cr, "GATE ATTENUATION", px + 38, y + 273, 17, AMBER)
        gain_rect = (px, y + 289, pw, 65)
        _grid(cr, gain_rect, low=-84, ticks=(0, -42, -84))
        _trace(cr, gains, gain_rect, AMBER, fill="top")
        _history_axis(cr, px, y + 358, pw)
    else:
        _display_badge(cr, x + 21, y + 17, 143, "TRANSFER", True)
        _display_badge(cr, x + 169, y + 17, 112, "INPUT")
        _display_badge(cr, x + 286, y + 17, 171, "GAIN REDUCTION")
        tx, ty, tw, th = x + 49, y + 88, 200, 244
        rect = (tx, ty, tw, th)
        _grid(cr, rect, -60, 0, (0, -20, -40, -60))
        for db in (-60, -40, -20, 0):
            _text(cr, str(db), tx + (db + 60) / 60 * tw, ty + th + 23,
                  14, (.65, .73, .62), centered=True)
        cr.set_dash([5, 5])
        _line(cr, [(tx, ty + th), (tx + tw, ty)], (.74, .77, .62), 1, .7)
        cr.set_dash([])
        threshold, ratio, makeup = transfer
        curve = []
        for i in range(101):
            db = -60 + i * .6
            output = transfer_output(db, threshold, ratio, makeup,
                                     details.get("knee", .01), on)
            curve.append((tx + i * tw / 100, ty + th * (1 - (max(-60, min(0, output)) + 60) / 60)))
        _static_signal_fill(cr, curve, ty + th, rect, GREEN)
        for thickness, alpha in ((9, .04), (5, .11), (2.2, 1)):
            _line(cr, curve, GREEN, thickness, alpha)
        threshold_x = tx + max(0, min(1, (threshold + 60) / 60)) * tw
        threshold_y = ty + th * (1 - max(0, min(1, (threshold + (makeup if on else 0) + 60) / 60)))
        cr.set_dash([6, 5])
        _line(cr, [(tx, threshold_y), (threshold_x, threshold_y),
                   (threshold_x, ty + th)], AMBER, 1.2, .8)
        cr.set_dash([])
        _radial(cr, threshold_x, threshold_y, 11,
                [(0, (1, .75, .3, .48)), (1, (1, .6, .1, 0))])
        _circle(cr, threshold_x, threshold_y, 3.7, (1, .9, .53))
        _text(cr, "STATIC TRANSFER · dB", tx + tw / 2, y + 382,
              14, DIM, centered=True)
        rx, rw = x + 297, w - 452
        _line(cr, [(rx, y + 70), (rx + 22, y + 70)], GREEN, 2)
        _text(cr, "INPUT", rx + 31, y + 75, 16, GREEN)
        input_rect = (rx, y + 88, rw, 128)
        _grid(cr, input_rect, -60, 0, (0, -20, -40, -60), True)
        _trace(cr, inputs, input_rect, GREEN, low=-60, fill=True)
        _text(cr, "GAIN REDUCTION", rx, y + 253, 16, AMBER)
        gain_rect = (rx, y + 270, rw, 79)
        # Positive attenuation magnitude: zero at the floor, 24 dB at the top.
        _grid(cr, gain_rect, 0, 24, (0, 12, 24), True)
        _trace(cr, [-gain for gain in gains], gain_rect, AMBER, low=0, high=24, fill=True)
        _history_axis(cr, rx, y + 358, rw)
    _glass(cr, x, y, w, h)
    if not online:
        _fill(cr, (.018, .035, .027), x + (w - 120) / 2 - 124, y + h / 2 - 18,
              248, 37, 4, .97)
        _text(cr, "NO INPUT DATA", x + (w - 120) / 2, y + h / 2 + 7,
              21, (.76, .84, .74), centered=True)


@lru_cache(maxsize=4)
def _panel_chrome(kind, model, state_items, focused, status, raster_scale):
    """The metal, switches and buttons stay cached while a value changes."""
    import cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 math.ceil(WIDTH * raster_scale),
                                 math.ceil(HEIGHT * raster_scale))
    surface.set_device_scale(raster_scale, raster_scale)
    cr = cairo.Context(surface)
    states = dict(state_items)
    cr.set_source_surface(faceplate("multiband" if model == 3 else kind), 0, 0)
    cr.paint()
    # Type belongs to the monitor-resolution layer, not the reusable metal
    # bitmap: downsizing pre-rasterized letters loses their hinted edges.
    title = ("MULTIBAND" if model == 3 else
             {"gate": "GATE", "comp": "COMPRESSOR", "band": "BAND DYNAMICS"}[kind])
    _engrave(cr, title, 145, 78, 32 if kind == "band" else 46,
             font="DejaVu Serif", bold=True)
    layout = controls(kind, model)
    if kind == "gate":
        buttons = (("gate_mode", "GATE", not states["gexp"]),
                   ("expander", "EXPANDER", states["gexp"]),
                   ("gklisten", "", states["gklisten"]))
        _engrave(cr, "MODE", 1126, 134, 19, centered=True, bold=True)
        _engrave(cr, "KEY LISTEN", 1126, 309, 17, centered=True, bold=True)
        _gradient(cr, 1065, 148, 123, 121,
                  [(0, (.19, .19, .16)), (.93, (.33, .33, .29)),
                   (1, (.94, .92, .85))], 6)
    else:
        _gradient(cr, 126, 397, 461 if kind == "band" else 615, 57,
                  [(0, (.19, .19, .16)), (.91, (.33, .33, .29)),
                   (1, (.94, .92, .85))], 6)
        _engrave(cr, "MODEL", 356 if kind == "band" else 433, 394,
                 15, centered=True, bold=True)
        buttons = [("model_" + str(i), name, model == i) for i, name in enumerate(
            ("STANDARD", "TUBE", "FET") if kind == "band" else
            ("STANDARD", "TUBE", "FET", "MULTIBAND"))]
        for key, title in (("knee", "SOFT KNEE"), ("auto", "AUTO"),
                           ("climit", "LIMIT"), ("cklisten", "KEY LISTEN"),
                           ("keyon", "KEY FILTER")):
            if key in layout:
                buttons.append((key, title, states.get(key, False)))
        if model == 3:
            _engrave(cr, "24 dB/OCT · FOUR BANDS", 776, 77, 22, bold=True)
            _engrave(cr, "HOST INSERT · " + status.upper(), 780, 431, 19, bold=True)
        if kind == "band":
            buttons.extend(("band_" + str(i), name, states["band"] == i)
                           for i, name in enumerate(BAND_NAMES))
    for key, name, active in buttons:
        if key in ("gklisten", "cklisten"):
            _listen_button(cr, layout[key], name, active, focused == key)
        else:
            _button(cr, layout[key], name, active, focused == key,
                    indicator=key in ("knee", "auto", "climit", "keyon"))
    if "power" in layout:
        _power(cr, layout["power"], states["power"], focused == "power")
    return surface


@lru_cache(maxsize=4)
def _panel_surface(kind, model, value_items, state_items, focused, hovered,
                   status, sample_rate, raster_scale):
    """Cache stationary artwork at device resolution; history stays separate.

    A value change only redraws its dial and parameter-dependent curves. Each
    constituent cache is bounded, including during continuous crossover drags.
    """
    import cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 math.ceil(WIDTH * raster_scale),
                                 math.ceil(HEIGHT * raster_scale))
    surface.set_device_scale(raster_scale, raster_scale)
    cr = cairo.Context(surface)
    values, states = dict(value_items), dict(state_items)
    specs = parameters(kind, model, states.get("band", 0))
    chrome_focus = None if any(spec.key == focused for spec in specs) else focused
    cr.set_source_surface(_panel_chrome(kind, model, state_items, chrome_focus,
                                        status, raster_scale), 0, 0)
    cr.paint()
    layout = controls(kind, model)
    for spec in specs:
        _cached_knob(cr, spec, values[spec.key], layout[spec.key],
                     focused == spec.key, hovered == spec.key,
                     kind != "gate" and model in (1, 3), raster_scale)
    if kind == "comp" and model == 3:
        _crossover_display(cr, values, {"sample_rate": sample_rate})
    return surface


def paint(cr, width, height, kind, model, values, states, history=(),
          online=False, transfer=(-24, 4, 0), focused=None, hovered=None,
          details=None):
    """Render the live rack. History entries are (input dB, measured GR dB)."""
    scale = min(width / WIDTH, height / HEIGHT)
    ox, oy = (width - WIDTH * scale) / 2, (height - HEIGHT * scale) / 2
    cr.save()
    # Center the rack on a physical pixel. A fractional translation would
    # resample the entire otherwise-native-resolution panel a second time.
    device_x, device_y = cr.user_to_device(ox, oy)
    sx, sy = cr.get_target().get_device_scale()
    ox, oy = cr.device_to_user(round(device_x * sx) / sx,
                               round(device_y * sy) / sy)
    cr.translate(ox, oy)
    cr.scale(scale, scale)
    details = details or {}
    # The caller's matrix includes monitor scaling, preserving crisp HiDPI art
    # while avoiding a full-rack resample on each measured-signal update.
    matrix = cr.get_matrix()
    raster_scale = math.hypot(matrix.xx, matrix.yx) * sx
    panel = _panel_surface(kind, model, tuple(sorted(values.items())),
                           tuple(sorted(states.items())), focused, hovered,
                           details.get("status", "Off"),
                           details.get("sample_rate", 48000), raster_scale)
    cr.set_source_surface(panel, 0, 0)
    cr.paint()
    if kind == "band":
        _band_display(cr, values, states, transfer, details)
    else:
        _display(cr, kind, model, values, history, online, states["power"], transfer, details)
    cr.restore()
