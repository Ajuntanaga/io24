"""Native-resolution enamel, amplifier hardware and phosphor response volumes.

Pure paint: no GTK, device, audio, timers or parameter state. The caller supplies
the measured rack geometry and the actual response. Text stays native in GTK.
"""
import math
import random

ORANGE = (1.0, .32, .055)
CREAM = (.96, .925, .83)
DARK_INK = (.12, .115, .10)
LIGHT_MODELS = frozenset(("hpf", "passive", "vintage"))


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
    # Fine powder coat and short directional machining, baked once per size.
    c.save()
    c.rectangle(left+2, 4, right-left-4, height-8)
    c.clip()
    rng = random.Random(924)
    for _ in range(int(width*height/80)):
        px, py = rng.uniform(left+3,right-3), rng.uniform(4,height-4)
        c.rectangle(px,py,.45+rng.random()*.7,.35)
        c.set_source_rgba(0,0,0,.035 if light else .16)
        c.fill()
    for n in range(2, int(height), 3):
        _line(c, [(left+3,n+.5),(right-3,n+.5)],
              (1,1,.94,.06 if light else .025), .5)
    c.restore()
    # Orange enamel seam, with a dark lower return: no coloured outer border.
    c.rectangle(left+1,height-6,right-left-2,2)
    c.set_source_rgba(*ORANGE,1)
    c.fill()
    _line(c, [(left+1,height-3),(right-1,height-3)], (0,0,0,.7), 1)
    for ex in (0,width-ear):
        _line(c, [(ex+ear-1,4),(ex+ear-1,height-4)], (.6,.62,.57,.26), .7)
        for ey in (height*.075,height*.89):
            sw, sh = ear*.57, max(7,height*.046)
            _round(c, ex+ear*.215,ey,sw,sh,sh/2)
            c.set_source_rgba(.38,.39,.36,.8)
            c.fill()
            _round(c, ex+ear*.215+.7,ey+.3,sw-1.4,sh-1.6,sh/2)
            c.set_source_rgba(.003,.005,.005,1)
            c.fill()
    for px in (left+width*.016,right-width*.016):
        for py in (height*.07,height*.91):
            _screw(c,px,py,max(3,width*.005))
    # A machined orange registration tab cuts into each side of the display.
    x,y,w,h = screen
    for px in (x-5,x+w+2):
        c.rectangle(px,y+h*.22,3,h*.14)
        c.set_source_rgba(*ORANGE,.95)
        c.fill()
    _glass(c,*screen)
    return surface


def amplifier_knob_surface(radius, angle, accent=ORANGE):
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
    # Broad, tangible bakelite flutes rather than a serrated metallic disc.
    for n in range(40):
        a = angle + n*math.tau/40
        p1=(math.cos(a)*55,math.sin(a)*55)
        p2=(math.cos(a)*62.3,math.sin(a)*62.3)
        light=max(0,math.cos(a+2.1))
        _line(c,[p1,p2],(.12+light*.15,.12+light*.14,.105+light*.12,1),3.2)
        _line(c,[(p1[0]+.6,p1[1]),(p2[0]+.6,p2[1])],(0,0,0,.8),.8)
    c.arc(0,0,54.5,0,math.tau)
    _gradient(c,-42,-54,38,54, (
        (0,(1,1,.94,1)), (.30,(.95,.93,.84,1)),
        (.70,(.68,.65,.55,1)), (1,(.36,.34,.28,1))))
    c.fill()
    c.arc(0,-1,48,0,math.tau)
    _gradient(c,-40,-48,34,48, (
        (0,(1,.995,.94,1)), (.4,(.97,.95,.86,1)),
        (1,(.83,.80,.69,1))))
    c.fill()
    c.arc(0,-1,47,0,math.tau)
    c.set_line_width(.8)
    c.set_source_rgba(1,1,.97,.8)
    c.stroke()
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


def toggle_surface(radius, active):
    """Short chrome bat lever inside the established circular hit target."""
    import cairo
    surface,c=_surface(math.ceil(radius*4),math.ceil(radius*3))
    c.translate(surface.get_width()/2,surface.get_height()/2)
    c.scale(radius/12,radius/12)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    _circle(c,1,2,11.5,(0,0,0,.55))
    _circle(c,0,0,10.5,(.02,.02,.018,1))
    c.move_to(9,0)
    for n in range(1,7):
        c.line_to(9*math.cos(n*math.tau/6),9*math.sin(n*math.tau/6))
    _gradient(c,-8,-8,8,8,((0,(1,1,.95,1)),(.35,(.62,.64,.61,1)),
                          (.55,(.17,.19,.18,1)),(1,(.65,.66,.61,1))))
    c.fill()
    _circle(c,0,0,5.6,(.05,.055,.05,1))
    tip=-9 if active else 9
    _line(c,[(1.5,2),(1.5,tip+2)],(0,0,0,.6),7)
    c.move_to(0,2 if active else -2)
    c.line_to(0,tip)
    _gradient(c,-4,0,4,0,((0,(.15,.16,.15,1)),(.32,(.86,.88,.84,1)),
                         (.50,(1,1,.96,1)),(.70,(.44,.47,.44,1)),
                         (1,(.10,.12,.11,1))))
    c.set_line_width(6)
    c.stroke()
    _line(c,[(-.7,tip-1),(-.7,tip+1)],(1,1,.98,.9),2)
    _circle(c,-18,0,3.8,(.06,.05,.035,1))
    _circle(c,-18,0,2.5,(*ORANGE,1) if active else (.22,.12,.055,1))
    if active:
        _circle(c,-18.5,-.6,.8,(1,.91,.62,1))
    return surface


def response_volume_surface(points, baseline, rect, colour, scale):
    """Extrude the supplied response into a bounded, translucent wire volume.

    Front edge retains exact data coordinates. Receding copies are a spatial
    projection, not invented audio history. At most 97 samples and 12 rows,
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
    rows=12
    # Back-to-front translucent ribbons form an illuminated curved object.
    for row in range(rows,0,-1):
        t=row/rows
        back=[project(p,t) for p in front]
        near=[project(p,(row-1)/rows) for p in front]
        c.move_to(*back[0])
        for p in back[1:]: c.line_to(*p)
        for p in reversed(near): c.line_to(*p)
        c.close_path()
        c.set_source_rgba(*colour,.023+.018*(1-t))
        c.fill()
        _line(c,back,(*colour,.13+.30*(1-t)),.55+.35*(1-t))
    for i in range(0,len(front),max(1,len(front)//36)):
        _line(c,[project(front[i],j/rows) for j in range(rows+1)],
              (*colour,.23),.6)
    # A dashed projected zero plane makes depth legible at flat EQ settings.
    for n in range(11):
        p=(w*n/10,base)
        _line(c,[project(p,0),project(p,1)],(*colour,.075),.6)
    _line(c,front,(*colour,.14),7)
    _line(c,front,(*colour,.28),3)
    _line(c,front,(1,.66,.32,.95),1.1)
    return surface
