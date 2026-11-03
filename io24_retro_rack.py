"""Native-resolution enamel, amplifier hardware and phosphor response volumes.

Pure paint: no GTK, device, audio, timers or parameter state. The caller supplies
the measured rack geometry and the actual response. Text stays native in GTK.
"""
import math
import random

ORANGE = (1.0, .32, .055)
CREAM = (.96, .925, .83)
DARK_INK = (.12, .115, .10)
LIGHT_MODELS = frozenset(("hpf", "passive", "vintage", "selector", "reverb"))


def ink(model):
    return DARK_INK if model in LIGHT_MODELS else CREAM


def _surface(width, height, scale=1):
    import cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 max(1, math.ceil(width * scale)),
                                 max(1, math.ceil(height * scale)))
    ctx = cairo.Context(surface)
    ctx.scale(scale, scale)
    return surface, ctx


def _round(c, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    c.new_sub_path()
    for cx, cy, start in ((x+w-r, y+r, -math.pi/2),
                          (x+w-r, y+h-r, 0),
                          (x+r, y+h-r, math.pi/2),
                          (x+r, y+r, math.pi)):
        c.arc(cx, cy, r, start, start+math.pi/2)
    c.close_path()


def _gradient(c, x0, y0, x1, y1, stops):
    import cairo
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for position, colour in stops:
        g.add_color_stop_rgba(position, *colour)
    c.set_source(g)


def _circle(c, x, y, r, colour):
    c.new_path()
    c.arc(x, y, r, 0, math.tau)
    c.set_source_rgba(*colour)
    c.fill()


def _line(c, points, colour, width=1):
    if not points:
        return
    c.new_path()
    c.move_to(*points[0])
    for p in points[1:]:
        c.line_to(*p)
    c.set_source_rgba(*colour)
    c.set_line_width(width)
    c.stroke()


def _screw(c, x, y, r):
    _circle(c, x+.7, y+1.1, r*1.15, (0, 0, 0, .65))
    c.arc(x, y, r, 0, math.tau)
    _gradient(c, x-r, y-r, x+r, y+r, (
        (0, (.88, .87, .81, 1)), (.35, (.43, .44, .42, 1)),
        (.56, (.09, .10, .10, 1)), (1, (.44, .44, .40, 1))))
    c.fill()
    _line(c, [(x-r*.50, y+r*.20), (x+r*.50, y-r*.20)], (0,0,0,.9), r*.23)
    _line(c, [(x-r*.50, y+r*.20+.6), (x+r*.50, y-r*.20+.6)], (1,1,.9,.3), .5)


def _glass(c, x, y, w, h):
    """Cut aluminium bevel, black gasket and an optically separate glass well."""
    _round(c, x-4, y-3, w+8, h+10, 8)
    c.set_source_rgba(0, 0, 0, .38)
    c.fill()
    _round(c, x, y, w, h, 7)
    _gradient(c, x, y, x, y+h, (
        (0, (.035,.037,.036,1)), (.035,(.30,.31,.29,1)),
        (.075,(.075,.076,.069,1)), (.94,(.025,.026,.025,1)),
        (1,(.48,.48,.43,1))))
    c.fill()
    _round(c, x+5, y+5, w-10, h-10, 4)
    _gradient(c, x, y, x+w*.65, y+h, (
        (0,(.018,.021,.021,1)), (.46,(.003,.005,.006,1)),
        (1,(.023,.012,.007,1))))
    c.fill()
    # Inset optical reflections are confined to the glass, never over type.
    _line(c, [(x+10,y+7),(x+w-10,y+7)], (.81,.80,.72,.22), .8)
    _line(c, [(x+7,y+10),(x+7,y+h-10)], (0,0,0,.9), 2)
    _line(c, [(x+10,y+h-6),(x+w-10,y+h-6)], (*ORANGE,.26), .7)


def _powder_coat(c, x, y, width, height, seed=924, density=22):
    """Fine raised enamel grain, clipped by the caller and baked into the paint."""
    rng = random.Random(seed)
    for _ in range(int(width * height / density)):
        px, py = rng.uniform(x, x+width), rng.uniform(y, y+height)
        r = rng.uniform(.28, .62)
        _circle(c, px+.18, py+.25, r, (.24, .25, .23, .10))
        _circle(c, px-.13, py-.17, r*.72, (1, 1, .98, .34))


def chassis_surface(width, height, scale, model, screen):
    surface, c = _surface(width, height, scale)
    light = model in LIGHT_MODELS
    ear = width * 80/2156
    left, right = ear, width-ear
    # Extruded black perimeter and continuous mechanically aligned ears.
    _round(c, 0, 0, width, height, 5)
    _gradient(c, 0, 0, 0, height, (
        (0,(.22,.23,.22,1)), (.025,(.055,.058,.057,1)),
        (.90,(.012,.014,.014,1)), (1,(.15,.16,.15,1))))
    c.fill()
    _round(c, left, 2, right-left, height-4, 3)
    stops = ((0,(1,1,.98,1)), (.04,(.97,.97,.94,1)),
             (.55,(.92,.93,.91,1)), (.96,(.85,.87,.85,1)),
             (1,(.60,.63,.61,1))) if light else (
        (0,(.29,.29,.27,1)), (.025,(.085,.088,.085,1)),
        (.38,(.029,.033,.032,1)), (.90,(.014,.017,.017,1)),
        (1,(.08,.087,.082,1)))
    _gradient(c, 0, 0, 0, height, stops)
    c.fill()
    # These white units have integral coated ears, with only the thin
    # folded perimeter and the mounting slots exposing the dark return.
    coated_ears = model in ("passive", "vintage", "selector", "reverb")
    if coated_ears:
        for ex in (1, right):
            _round(c, ex, 2, ear-1, height-4, 2)
            _gradient(c, 0, 0, 0, height, stops)
            c.fill()
    # The white finish is stippled enamel, not horizontal brushed stripes.
    c.save()
    texture_left = 2 if coated_ears else left+2
    texture_right = width-2 if coated_ears else right-2
    c.rectangle(texture_left, 4, texture_right-texture_left, height-8)
    c.clip()
    if light:
        _powder_coat(c, texture_left, 4, texture_right-texture_left, height-8)
    else:
        rng = random.Random(924)
        for _ in range(int(width*height/80)):
            px, py = rng.uniform(left+3,right-3), rng.uniform(4,height-4)
            c.rectangle(px,py,.45+rng.random()*.7,.35)
            c.set_source_rgba(0,0,0,.16)
            c.fill()
        for n in range(2, int(height), 3):
            _line(c, [(left+3,n+.5),(right-3,n+.5)], (1,1,.94,.025), .5)
    c.restore()
    # Orange enamel seam, with a dark lower return: no coloured outer border.
    c.rectangle(left+1,height-6,right-left-2,2)
    c.set_source_rgba(*ORANGE,1)
    c.fill()
    _line(c, [(left+1,height-3),(right-1,height-3)], (0,0,0,.7), 1)
    for ex in (0,width-ear):
        _line(c, [(ex+ear-1,4),(ex+ear-1,height-4)], (.6,.62,.57,.26), .7)
        for ey in ((height/2-3.5,) if model == "selector" else
                   (height*.075,height*.89)):
            sw, sh = ear*.57, max(7,height*.046)
            _round(c, ex+ear*.215,ey,sw,sh,sh/2)
            c.set_source_rgba(.38,.39,.36,.8)
            c.fill()
            _round(c, ex+ear*.215+.7,ey+.3,sw-1.4,sh-1.6,sh/2)
            c.set_source_rgba(.003,.005,.005,1)
            c.fill()
    for px in ((ear/2, width-ear/2) if model == "selector" else
               (left+width*.016,right-width*.016)):
        for py in ((height/2,) if model == "selector" else
                   (height*.07,height*.91)):
            _screw(c,px,py,max(3,width*.005))
    # A machined orange registration tab cuts into each side of the display.
    if screen is not None:
        x,y,w,h = screen
        for px in (x-5,x+w+2):
            c.rectangle(px,y+h*.22,3,h*.14)
            c.set_source_rgba(*ORANGE,.95)
            c.fill()
        _glass(c,*screen)
    return surface


def amplifier_knob_surface(radius, angle, accent=ORANGE, powder_coated=False):
    """Ivory amplifier knob: rotating scalloped rubber skirt, flat cap.

    The index and knurling rotate with the control. World-space light stays
    fixed, so turning the knob never rotates a baked shadow or highlight.
    """
    import cairo
    size = math.ceil(radius*2.6)
    surface,c = _surface(size,size)
    c.translate(size/2,size/2)
    c.scale(radius/64,radius/64)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for r,a in ((71,.08),(69,.13),(66,.24)):
        _circle(c,1.8,4.5,r,(0,0,0,a))
    _circle(c,0,1,64,(.012,.013,.012,1))
    if powder_coated:
        c.arc(0,0,62.8,0,math.tau)
        _gradient(c,-45,-54,45,54,(
            (0,(.69,.73,.69,1)),(.38,(.49,.54,.50,1)),
            (1,(.24,.29,.25,1))))
        c.fill()
    # The skirt has actual recesses and a separate bevel under the flat cap.
    for n in range(40):
        a = angle + n*math.tau/40
        p1=(math.cos(a)*55,math.sin(a)*55)
        p2=(math.cos(a)*62.3,math.sin(a)*62.3)
        light=max(0,math.cos(a+2.1))
        tone = ((.34+light*.36,.37+light*.36,.34+light*.35,1)
                if powder_coated else
                (.12+light*.15,.12+light*.14,.105+light*.12,1))
        _line(c,[p1,p2],tone,3.2)
        _line(c,[(p1[0]+.6,p1[1]),(p2[0]+.6,p2[1])],
              (0,0,0,.65 if powder_coated else .8),1.15)
    c.arc(0,0,54.5,0,math.tau)
    shoulder = (
        (0,(.87,.91,.86,1)), (.27,(.74,.79,.74,1)),
        (.63,(.46,.52,.47,1)), (1,(.22,.28,.24,1))) if powder_coated else (
        (0,(1,1,.94,1)), (.30,(.95,.93,.84,1)),
        (.70,(.68,.65,.55,1)), (1,(.36,.34,.28,1)))
    _gradient(c,-42,-54,38,54,shoulder)
    c.fill()
    if powder_coated:
        c.save()
        c.arc(0,0,62.5,0,math.tau)
        c.arc_negative(0,0,48,math.tau,0)
        c.clip()
        c.rotate(angle)
        _powder_coat(c,-64,-64,128,128,seed=215,density=13)
        c.restore()
    c.arc(0,-1,48,0,math.tau)
    cap = (
        (0,(.995,1,.98,1)), (.45,(.96,.97,.94,1)),
        (1,(.88,.90,.86,1))) if powder_coated else (
        (0,(1,.995,.94,1)), (.4,(.97,.95,.86,1)),
        (1,(.83,.80,.69,1)))
    _gradient(c,-40,-48,34,48,cap)
    c.fill()
    c.arc(0,-1,47,0,math.tau)
    c.set_line_width(.8)
    c.set_source_rgba(1,1,.97,.8)
    c.stroke()
    if powder_coated:
        c.save()
        c.arc(0,-1,46.5,0,math.tau)
        c.clip()
        c.rotate(angle)
        _powder_coat(c,-48,-49,96,96,seed=716,density=10)
        c.restore()
    else:
        # Almost invisible concentric machining on the flat cap, with no bump.
        for r in range(16,46,3):
            c.arc(0,-1,r,0,math.tau)
            c.set_source_rgba(.35,.31,.22,.035)
            c.set_line_width(.45)
            c.stroke()
    dx,dy=math.cos(angle),math.sin(angle)
    _line(c,[(dx*20,dy*20),(dx*43,dy*43)],(.12,.105,.075,1),4)
    # Recessed orange index continues down the shoulder, fixed to the body.
    _line(c,[(dx*50,dy*50),(dx*60,dy*60)],(*accent,1),3.2)
    return surface


def toggle_contains(cx, cy, radius, x, y):
    """Cover the whole bat in either position, with a comfortable minimum hit area."""
    return (radius > 0 and abs(float(x)-cx) <= max(18, radius*1.5)
            and abs(float(y)-cy) <= max(24, radius*2.1))


def toggle_surface(radius, active):
    """Use exactly the Gate/Comp hardware on every effects rack."""
    from io24_dynamics_rack import power_hardware
    size = math.ceil(radius * 5.8)
    surface, c = _surface(size, size)
    c.translate(size / 2, size / 2)
    c.scale(radius / 35, radius / 35)
    power_hardware(c, 0, 0, active)
    return surface


def response_volume_surface(points, baseline, rect, colour, scale, mesh_depth=False):
    """Extrude the supplied response into a bounded, translucent wire volume.

    Front edge retains exact data coordinates. Receding copies are a spatial
    projection, not invented audio history. At most 97 samples and 18 rows,
    independent of the display's pixel count.
    """
    x,y,w,h=rect
    surface,c=_surface(w,h,scale)
    if len(points)<2 or w<=0 or h<=0:
        return surface
    c.rectangle(0,0,w,h)
    c.clip()
    stride=max(1,math.ceil(len(points)/96))
    front=[(px-x,py-y) for px,py in points[::stride]]
    if front[-1] != (points[-1][0]-x,points[-1][1]-y):
        front.append((points[-1][0]-x,points[-1][1]-y))
    base=baseline-y
    def project(p,t):
        px,py=p
        if mesh_depth:
            return (w*.49+(px-w*.49)*(1-t*.24)+w*.035*t,
                    base-h*.34*t+(py-base)*(1-t*.58))
        return (w*.50+(px-w*.50)*(1-t*.18)+w*.035*t,
                h*.18+(py-h*.18)*(1-t*.38)-h*.09*t)
    # Warm optical density below the real envelope.
    c.move_to(*front[0])
    for p in front[1:]: c.line_to(*p)
    c.line_to(front[-1][0],base)
    c.line_to(front[0][0],base)
    c.close_path()
    _gradient(c,0,min(p[1] for p in front),0,h,
              ((0,(*colour,.26)),(1,(*colour,.015))))
    c.fill()
    rows=18 if mesh_depth else 12
    # Back-to-front translucent ribbons form an illuminated curved object.
    for row in range(rows,0,-1):
        t=row/rows
        back=[project(p,t) for p in front]
        near=[project(p,(row-1)/rows) for p in front]
        c.move_to(*back[0])
        for p in back[1:]: c.line_to(*p)
        for p in reversed(near): c.line_to(*p)
        c.close_path()
        c.set_source_rgba(*colour,(.05 if mesh_depth else .023)+.018*(1-t))
        c.fill()
        _line(c,back,(*colour,.17+.30*(1-t)),.55+.35*(1-t))
        if mesh_depth:
            # Diagonal threads and shaded facets make one woven surface;
            # their heights come exclusively from the supplied EQ response.
            for i in range(0,len(front)-2,2):
                a,b,d = back[i],back[i+2],near[i+2]
                slope = min(1,abs(front[i+2][1]-front[i][1])/max(h*.08,1))
                c.move_to(*a)
                c.line_to(*b)
                c.line_to(*d)
                c.close_path()
                c.set_source_rgba(*colour,.018+.055*slope)
                c.fill()
                _line(c,[a,d],(*colour,.11+.09*(1-t)),.5)
    for i in range(0,len(front),max(1,len(front)//36)):
        _line(c,[project(front[i],j/rows) for j in range(rows+1)],
              (*colour,.36 if mesh_depth else .23),.65)
    # A dashed projected zero plane makes depth legible at flat EQ settings.
    for n in range(11):
        p=(w*n/10,base)
        _line(c,[project(p,0),project(p,1)],(*colour,.075),.6)
    _line(c,front,(*colour,.14),7)
    _line(c,front,(*colour,.28),3)
    _line(c,front,(1,.66,.32,.95),1.1)
    return surface


def reverb_mesh_project(point, rect):
    """Oblique camera shared by the surface, plinth and depth markers."""
    x, y, w, h = rect
    t, lane, relief = point
    far = (1.0 - lane) * .5
    return (x + w * (.025 + t * .84 + far * .11),
            y + h * (.98 - far * .36 - t * .12 - relief * .62))


def reverb_facet_light(triangle):
    """Diffuse face lighting in world space, independent of window size."""
    a, b, c = triangle
    u = ((b[0]-a[0])*3.0, (b[1]-a[1])*.65, b[2]-a[2])
    v = ((c[0]-a[0])*3.0, (c[1]-a[1])*.65, c[2]-a[2])
    nx, ny, nz = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2],
                  u[0]*v[1]-u[1]*v[0])
    length = max(1e-9, math.sqrt(nx*nx + ny*ny + nz*nz))
    return max(0.0, min(1.0, (-.35*nx - .45*ny + .82*nz) / length))


def reverb_mesh_surface(width, height, scale, mesh, triangles, gap, active):
    """Rasterize one bounded chamber frame, with depth-ordered 3D facets.

    Cairo draws the small display into one native-resolution GTK texture;
    hundreds of individual GSK stroke/fill nodes cost too much per frame.
    Geometry and parameter state belong to the caller. No audio or timers.
    """
    surface, c = _surface(width, height, scale)
    lit = 1.0 if active else .30
    viewport = (17, 23, width - 34, height - 43)
    project = lambda point: reverb_mesh_project(point, viewport)
    base = lambda point: project((point[0], point[1], 0.0))
    projected = {p: project(p) for row in mesh["rows"] for p in row}
    c.rectangle(8, 20, width - 16, height - 36)
    c.clip()

    def polygon(points, colour, edge=None):
        c.new_path()
        c.move_to(*points[0])
        for point in points[1:]:
            c.line_to(*point)
        c.close_path()
        c.set_source_rgba(*colour)
        if edge is None:
            c.fill()
        else:
            c.fill_preserve()
            c.set_source_rgba(*edge)
            c.set_line_width(.65)
            c.stroke()

    # The floor and the volume share a camera. Pre-delay is an empty stretch
    # of floor up to the ignition edge; the camera never moves with a control.
    corners = [project(p) for p in ((0, -1, 0), (1, -1, 0),
                                    (1, 1, 0), (0, 1, 0))]
    polygon(corners, (.08*lit, .035*lit, .012*lit, 1))
    for index in range(9):
        lane = -1 + index / 4
        _line(c, [project((0, lane, 0)), project((1, lane, 0))],
              (*ORANGE, .13*lit), .6)
    for index in range(25):
        t = index / 24
        _line(c, [project((t, -1, 0)), project((t, 1, 0))],
              (*ORANGE, (.22 if index % 4 == 0 else .11)*lit), .6)
    _line(c, corners + corners[:1], (*ORANGE, .38*lit), .8)
    _line(c, [project((gap, -1, 0)), project((gap, 1, 0))],
          (*CREAM, .42*lit), .8)

    # 640 triangles: back-to-front opaque faces and fine cross-weaving.
    for triangle in sorted(triangles,
                           key=lambda tri: sum(p[1] - p[0]*.24 for p in tri)):
        relief = sum(p[2] for p in triangle) / 3
        light = reverb_facet_light(triangle)
        shade = .10 + .34*light + .20*relief
        polygon([projected[p] for p in triangle],
                (shade*lit, (.025 + shade*.24)*lit,
                 (.009 + shade*.035)*lit, 1),
                (1, .25 + light*.20, .065, (.26 + light*.29)*lit))

    # Dark cut faces connect the moving skin to its floor.
    for edge in (mesh["columns"][0], mesh["rows"][-1]):
        for a, b in zip(edge, edge[1:]):
            polygon([projected[a], projected[b], base(b), base(a)],
                    (.13*lit, .031*lit, .008*lit, 1))
        _line(c, [projected[p] for p in edge], (*ORANGE, .92*lit), 1)
        for point in edge[::2]:
            _line(c, [base(point), projected[point]], (*ORANGE, .26*lit), .6)

    # Ivory seams and sparse illuminated junctions; no fuzzy glow passes.
    for index in (0, len(mesh["rows"]) // 2):
        _line(c, [projected[p] for p in mesh["rows"][index]],
              (*CREAM, (.36 if index == 0 else .82)*lit), .85)
    for row in mesh["rows"][2:-1:3]:
        for point in row[2:-1:5]:
            if point[2] > .13:
                px, py = projected[point]
                _circle(c, px, py, .85, (*CREAM, .80*lit))
    return surface
