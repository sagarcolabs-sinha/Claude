"""
cartoon-doc engine — draws 2D cartoon documentary frames in code.
Requires: pycairo, numpy, ffmpeg.   pip install pycairo numpy (in a venv)
Fonts: Caveat (+ Patrick Hand) in ~/.fonts  (see SKILL.md setup).

A video = a list of Scene objects. Each scene has a draw(c, t, tg) function that
calls cam(c, depth) before each depth layer, plus a SHOT LIST that drives the camera.
"""
import cairo, math, subprocess, numpy as np

W, H, FPS = 1080, 1920, 30   # vertical 9:16 for Shorts
END_FADE = True              # False = no fade at the end, so a Short loops cleanly
OVERLAY = None               # optional f(c, tg) drawn in screen space on top of every frame
INK = (0.09, 0.08, 0.08)

# ------------------------------------------------------------------ math / easing
def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3                 # ease-out
def ease_in(x): x = clamp(x); return x ** 3
def smooth(x): x = clamp(x); return x * x * (3 - 2 * x)
def back(x):                                                         # pop with overshoot
    x = clamp(x); k = 1.9; return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2
def lerp(a, b, k): return a + (b - a) * k
def rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

# ------------------------------------------------------------------ camera
TNOW = 0.0
CAM = [W / 2, H / 2, 1.0, 0.0, 0.0]          # cx, cy, zoom, shake-x, shake-y

def cam(c, d=1.0):
    """Apply the virtual camera with parallax depth d. bg 0.6-0.8, main 1.0, foreground 1.1-1.2."""
    cx, cy, z, sx, sy = CAM
    zd = 1 + (z - 1) * d
    c.identity_matrix()
    c.translate(W / 2 + sx * d, H / 2 + sy * d); c.scale(zd, zd)
    c.translate(-(W / 2 + (cx - W / 2) * d), -(H / 2 + (cy - H / 2) * d))

def screen(c): c.identity_matrix()                   # for labels / vignette

# ------------------------------------------------------------------ drawing primitives
def rr(c, x, y, w, h, r):
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0); c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi); c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()

def fs(c, col, lw=5, a=1.0):                          # fill + ink outline (THE house look)
    c.set_source_rgba(*col, a); c.fill_preserve()
    c.set_source_rgba(*INK, a); c.set_line_width(lw); c.stroke()

def fill(c, col, a=1.0): c.set_source_rgba(*col, a); c.fill()

def line(c, x0, y0, x1, y1, lw=5, col=INK, a=1.0):
    c.move_to(x0, y0); c.line_to(x1, y1); c.set_source_rgba(*col, a); c.set_line_width(lw); c.stroke()

def poly(c, pts):
    c.move_to(*pts[0])
    for p in pts[1:]: c.line_to(*p)
    c.close_path()

def glow(c, cx, cy, r, col, a=0.6):                   # soft light pool
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    g.add_color_stop_rgba(0, *col, a); g.add_color_stop_rgba(1, *col, 0)
    c.set_source(g); c.arc(cx, cy, r, 0, 2 * math.pi); c.fill()

def vgrad(c, x, y, w, h, top, bot):
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bot)
    c.set_source(g); c.rectangle(x, y, w, h); c.fill()

def text(c, s, x, y, size, col=(1, 1, 1), font='Caveat', align='c', bold=True, a=1.0):
    c.select_font_face(font, cairo.FONT_SLANT_NORMAL,
                       cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size)
    e = c.text_extents(s)
    if align == 'c': x -= e.x_advance / 2
    elif align == 'r': x -= e.x_advance
    c.move_to(x, y); c.set_source_rgba(*col, a); c.show_text(s)
    return e.x_advance

def text_width(c, s, size, font='Caveat'):
    c.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
    return c.text_extents(s).x_advance

def star(c, x, y, r_out, r_in, n=5):
    pts = []
    for k in range(n * 2):
        a = -math.pi / 2 + k * math.pi / n; r = r_out if k % 2 == 0 else r_in
        pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
    poly(c, pts)

def vignette(c, strength=0.75):
    d = math.hypot(W, H) / 2
    g = cairo.RadialGradient(W / 2, H / 2, d * 0.45, W / 2, H / 2, d * 1.05)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, strength)
    c.set_source(g); c.paint()

_rng = np.random.default_rng(7)
_n = _rng.integers(0, 255, (H, W), dtype=np.uint8)
_g = np.zeros((H, W, 4), dtype=np.uint8); _g[..., 0] = _g[..., 1] = _g[..., 2] = _n; _g[..., 3] = 255
GRAIN = cairo.ImageSurface.create_for_data(_g, cairo.FORMAT_ARGB32, W, H)

# ------------------------------------------------------------------ characters
def talking(t, span):
    """mouth openness while a voice line plays; span=(start,end) in the same clock as t"""
    if span and span[0] <= t <= span[1]:
        return 0.55 + 0.45 * math.sin(t * 31) * math.sin(t * 13 + 1)
    return 0.0

def blinking(t, seed): return ((t + seed) % 3.7) < 0.12

def person(c, x, y, s=1.0, skin='#f2c9a0', shirt='#3b5b8c', pants='#2b2b33', hair='#2a1d16',
           style='short', hat=None, beard=None, glasses=False, sunglasses=False, mouth=0.0,
           armL=0.15, armR=-0.15, tie=None, jacket=None, robe=None, flip=False, blink=False,
           headrot=0.0, walk=0.0, prop=None, mood='neutral'):
    """
    The house character: big round head, dot eyes, bean body, stick limbs, thick ink outline.
    x,y = feet position. s=1 -> about 345 px tall.
    style: short | slick | bald | long | bob | curly | wild | bun | none
    hat:   None | cap (soda) | helmet (soldier) | tophat | crown | beret | hardhat | hood | headband | cowboy
    beard: None | stubble | full | long  (colour = hair)
    robe:  colour hex -> long robe/tunic instead of shirt+pants (ancient, medieval, monks)
    arms:  angle in radians from hanging down; + outward, - forward; ~2.6 = raised overhead
    mood:  neutral | happy | worried | angry | shocked   (changes brows/mouth)
    prop:  None | callable(c, hand_x, hand_y) drawn at the right hand
    """
    sk, sh, pa, ha = rgb(skin), rgb(shirt), rgb(pants), rgb(hair)
    c.save(); c.translate(x, y)
    if flip: c.scale(-1, 1)
    c.scale(s, s); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.save(); c.scale(1, 0.18); c.arc(0, 0, 70, 0, 2 * math.pi); c.restore(); fill(c, (0, 0, 0), 0.25)
    bob = abs(math.sin(TNOW * 2.1 + x * 0.013)) * 4 + abs(math.sin(TNOW * 9)) * 10 * walk
    c.translate(0, -bob)
    legswing = math.sin(TNOW * 9) * 0.35 * walk
    if not robe:
        for k_, dx in enumerate((-16, 16)):
            fx = dx * 1.1 + (legswing if k_ else -legswing) * 60
            line(c, dx, -70, fx, -4, 15); line(c, dx, -70, fx, -4, 8, pa)
    hands = []
    for side, ang in ((-1, armL), (1, armR)):
        sx, sy = side * 40, -178
        ex, ey = sx + side * math.sin(ang) * 86, sy + math.cos(ang) * 86
        sleeve = rgb(jacket) if jacket else (rgb(robe) if robe else sh)
        line(c, sx, sy, ex, ey, 15); line(c, sx, sy, ex, ey, 8, sleeve)
        c.arc(ex, ey, 9, 0, 2 * math.pi); fs(c, sk, 4); hands.append((ex, ey))
    if robe:
        poly(c, [(-44, -205), (44, -205), (62, -4), (-62, -4)]); fs(c, rgb(robe), 5)
        line(c, -40, -120, 40, -120, 6, (0, 0, 0), 0.25)
    else:
        c.save(); c.translate(0, -135); c.scale(1, 1.42); c.arc(0, 0, 50, 0, 2 * math.pi); c.restore()
        fs(c, rgb(jacket) if jacket else sh, 5)
        if jacket: poly(c, [(-16, -200), (0, -150), (16, -200)]); fs(c, sh, 3)
        if tie: poly(c, [(-6, -196), (6, -196), (8, -140), (0, -128), (-8, -140)]); fs(c, rgb(tie), 3)
    # ---- head group (tilts / nods / shakes)
    hy = -270
    tilt = headrot + 0.035 * math.sin(TNOW * 1.3 + x * 0.007) + (0.05 * math.sin(TNOW * 8) if mouth > 0.08 else 0)
    c.save(); c.translate(0, hy - 40); c.rotate(tilt); c.translate(0, -(hy - 40))
    if style == 'long':   # hair behind head
        rr(c, -82, hy - 40, 164, 150, 40); fs(c, ha, 5)
    if style == 'wild':
        for k in range(14):
            a = math.pi * (0.9 + k / 13 * 1.2)
            c.arc(math.cos(a) * 70, hy + math.sin(a) * 70, 26, 0, 2 * math.pi); fs(c, ha, 4)
    c.arc(0, hy, 74, 0, 2 * math.pi); fs(c, sk, 5)
    if beard:
        if beard == 'stubble':
            c.arc(0, hy + 8, 62, 0.15 * math.pi, 0.85 * math.pi); c.set_source_rgba(*ha, 0.35); c.set_line_width(22); c.stroke()
        else:
            ln = 60 if beard == 'full' else 120
            c.move_to(-68, hy + 6); c.curve_to(-64, hy + 30 + ln, 64, hy + 30 + ln, 68, hy + 6)
            c.curve_to(40, hy + 62, -40, hy + 62, -68, hy + 6); c.close_path(); fs(c, ha, 4)
    if style == 'short':
        c.arc(0, hy, 74, math.pi * 1.05, math.pi * 1.95); c.close_path(); fs(c, ha, 5)
    elif style == 'slick':
        c.move_to(-74, hy - 4); c.curve_to(-70, hy - 95, 70, hy - 95, 74, hy - 4)
        c.curve_to(40, hy - 40, -20, hy - 55, -74, hy - 4); c.close_path(); fs(c, ha, 5)
    elif style == 'bald':
        for sd in (-1, 1):
            c.move_to(sd * 72, hy - 10); c.curve_to(sd * 86, hy - 40, sd * 60, hy - 52, sd * 52, hy - 46)
            c.curve_to(sd * 62, hy - 30, sd * 66, hy - 18, sd * 72, hy - 10); c.close_path(); fs(c, ha, 3)
    elif style in ('bob', 'long'):
        c.arc(0, hy, 76, math.pi * 1.0, math.pi * 2.0); c.close_path(); fs(c, ha, 5)
        if style == 'bob':
            rr(c, -82, hy - 20, 26, 90, 12); fs(c, ha, 4); rr(c, 56, hy - 20, 26, 90, 12); fs(c, ha, 4)
    elif style == 'curly':
        for k in range(9):
            a = math.pi * (1.0 + k / 8); c.arc(math.cos(a) * 66, hy + math.sin(a) * 66, 22, 0, 2 * math.pi); fs(c, ha, 4)
    elif style == 'bun':
        c.arc(0, hy - 82, 30, 0, 2 * math.pi); fs(c, ha, 4)
        c.arc(0, hy, 74, math.pi * 1.05, math.pi * 1.95); c.close_path(); fs(c, ha, 5)
    elif style == 'wild':
        c.arc(0, hy, 74, math.pi * 1.1, math.pi * 1.9); c.close_path(); fs(c, ha, 4)
    # eyes / brows / mouth
    for dx in (-25, 25):
        if blink: line(c, dx - 7, hy - 2, dx + 7, hy - 2, 4)
        else: c.arc(dx, hy - 2, 6.5, 0, 2 * math.pi); fill(c, INK)
    if mood in ('worried', 'angry'):
        # inner ends (towards the nose) go DOWN for angry, UP for worried. y grows downwards.
        k = 1 if mood == 'angry' else -1
        for dx in (-25, 25):
            side = -1 if dx < 0 else 1                 # -1 = left brow, +1 = right brow
            xo, xi = dx + side * 12, dx - side * 12   # outer end, inner end
            yo, yi = hy - 20 - 6 * k, hy - 20 + 6 * k
            line(c, xo, yo, xi, yi, 10, sk)           # skin-coloured halo so brows read over dark hair
            line(c, xo, yo, xi, yi, 4)
    if glasses:
        c.set_source_rgb(*INK); c.set_line_width(4)
        for dx in (-25, 25): c.arc(dx, hy - 2, 19, 0, 2 * math.pi); c.stroke()
        line(c, -6, hy - 4, 6, hy - 4, 4)
    if sunglasses:
        for dx in (-25, 25): rr(c, dx - 21, hy - 15, 42, 26, 8); fill(c, INK)
        line(c, -6, hy - 6, 6, hy - 6, 4)
    if mouth > 0.08 or mood == 'shocked':
        mo = max(mouth, 0.8 if mood == 'shocked' else 0)
        c.save(); c.translate(0, hy + 34); c.scale(1, 0.35 + 0.65 * mo); c.arc(0, 0, 13, 0, 2 * math.pi); c.restore()
        fs(c, rgb('#6b1f1f'), 4)
    elif mood == 'happy':
        c.arc(0, hy + 22, 18, 0.1 * math.pi, 0.9 * math.pi); c.close_path(); fs(c, rgb('#6b1f1f'), 4)
    elif mood in ('worried', 'angry'):
        c.arc(0, hy + 44, 13, 1.2 * math.pi, 1.8 * math.pi); c.set_source_rgb(*INK); c.set_line_width(4); c.stroke()
    else:
        c.arc(0, hy + 26, 13, 0.25 * math.pi, 0.75 * math.pi); c.set_source_rgb(*INK); c.set_line_width(4); c.stroke()
    # hats
    if hat == 'cap':
        poly(c, [(-60, hy - 36), (60, hy - 36), (46, hy - 82), (-46, hy - 82)]); fs(c, (0.97, 0.97, 0.95), 5)
        c.rectangle(-60, hy - 48, 120, 10); fill(c, rgb('#c8312c'))
    elif hat == 'helmet':
        c.arc(0, hy - 18, 82, math.pi, 2 * math.pi); c.close_path(); fs(c, rgb('#556b3a'), 5)
        rr(c, -96, hy - 26, 192, 16, 8); fs(c, rgb('#4a5d33'), 4)
    elif hat == 'tophat':
        rr(c, -48, hy - 170, 96, 110, 6); fs(c, rgb('#1d1d22'), 5); rr(c, -80, hy - 70, 160, 18, 8); fs(c, rgb('#1d1d22'), 5)
    elif hat == 'crown':
        poly(c, [(-56, hy - 50), (-56, hy - 110), (-28, hy - 80), (0, hy - 120), (28, hy - 80), (56, hy - 110), (56, hy - 50)])
        fs(c, rgb('#e3b341'), 5)
    elif hat == 'beret':
        c.save(); c.translate(-10, hy - 62); c.scale(1.2, 0.5); c.arc(0, 0, 66, 0, 2 * math.pi); c.restore(); fs(c, rgb('#7a1f2b'), 5)
    elif hat == 'hardhat':
        c.arc(0, hy - 20, 78, math.pi, 2 * math.pi); c.close_path(); fs(c, rgb('#f2b632'), 5); rr(c, -92, hy - 28, 184, 14, 7); fs(c, rgb('#e0a21f'), 4)
    elif hat == 'cowboy':
        c.save(); c.translate(0, hy - 58); c.scale(1, 0.28); c.arc(0, 0, 120, 0, 2 * math.pi); c.restore(); fs(c, rgb('#8a5a2b'), 5)
        rr(c, -50, hy - 125, 100, 70, 22); fs(c, rgb('#8a5a2b'), 5)
    elif hat == 'hood':
        c.arc(0, hy, 90, math.pi * 0.85, math.pi * 2.15); c.set_source_rgb(*(rgb(robe) if robe else sh)); c.set_line_width(30); c.stroke()
    elif hat == 'headband':
        rr(c, -76, hy - 44, 152, 18, 8); fs(c, rgb('#c8312c'), 4)
    c.restore()                                   # end head group
    if prop: prop(c, *hands[1])
    c.restore()

def animal(c, x, y, s=1.0, kind='dog', col='#b07a46', col2=None, mouth=0.0, flip=False, walk=0.0, blink=False):
    """
    House-style quadruped. kind: dog | cat | horse | deer | bear | elephant | mammoth | wolf | lion | cow
    Same rules as people: round head, dot eye, ink outline, flat colour. x,y = ground under body centre.
    For birds/fish/reptiles build new shapes with the same rules (see SKILL.md).
    """
    b, b2 = rgb(col), rgb(col2 or col)
    big = kind in ('elephant', 'mammoth', 'horse', 'bear', 'cow')
    L = 1.5 if big else 1.0
    c.save(); c.translate(x, y)
    if flip: c.scale(-1, 1)
    c.scale(s, s)
    c.save(); c.scale(1, 0.16); c.arc(0, 0, 150 * L, 0, 2 * math.pi); c.restore(); fill(c, (0, 0, 0), 0.25)
    bob = abs(math.sin(TNOW * 2.0 + x * 0.01)) * 3 + abs(math.sin(TNOW * 8)) * 8 * walk
    c.translate(0, -bob)
    legh = 90 * L if kind not in ('horse', 'deer') else 150
    bodyy = -legh - 45 * L
    for k, lx in enumerate((-80 * L, -50 * L, 55 * L, 85 * L)):
        sw = math.sin(TNOW * 8 + k * 1.7) * 18 * walk
        line(c, lx, bodyy + 30, lx + sw, -4, 30 * (1.4 if big else 1)); line(c, lx, bodyy + 30, lx + sw, -4, 20 * (1.4 if big else 1), b2)
    if kind in ('dog', 'wolf', 'cat', 'lion', 'horse', 'cow', 'deer', 'bear'):
        ta = math.sin(TNOW * 4) * 0.3
        line(c, -110 * L, bodyy, -110 * L - math.cos(ta) * 70, bodyy - 40 + math.sin(ta) * 30, 14)
        line(c, -110 * L, bodyy, -110 * L - math.cos(ta) * 70, bodyy - 40 + math.sin(ta) * 30, 7, b)
    c.save(); c.translate(0, bodyy); c.scale(1.7 * L, 0.85 * L); c.arc(0, 0, 75, 0, 2 * math.pi); c.restore(); fs(c, b, 5)
    if kind == 'mammoth':
        for k in range(8):
            line(c, -100 + k * 28, bodyy - 30, -110 + k * 28, bodyy + 60, 6, (0, 0, 0), 0.18)
    hx, hy = 125 * L, bodyy - 55 * L
    hr = 52 * L
    if kind in ('horse', 'deer'): hx, hy = 150, bodyy - 110; line(c, 90, bodyy - 20, hx - 10, hy + 20, 40); line(c, 90, bodyy - 20, hx - 10, hy + 20, 30, b)
    if kind in ('elephant', 'mammoth'):
        c.move_to(hx + 30, hy + 10); c.curve_to(hx + 80, hy + 40, hx + 70, hy + 130, hx + 50, hy + 170)
        c.set_source_rgb(*INK); c.set_line_width(34); c.stroke()
        c.move_to(hx + 30, hy + 10); c.curve_to(hx + 80, hy + 40, hx + 70, hy + 130, hx + 50, hy + 170)
        c.set_source_rgb(*b); c.set_line_width(24); c.stroke()
        if kind == 'mammoth':
            c.move_to(hx + 20, hy + 40); c.curve_to(hx + 90, hy + 120, hx + 150, hy + 60, hx + 140, hy - 10)
            c.set_source_rgb(*INK); c.set_line_width(18); c.stroke()
            c.move_to(hx + 20, hy + 40); c.curve_to(hx + 90, hy + 120, hx + 150, hy + 60, hx + 140, hy - 10)
            c.set_source_rgb(0.96, 0.93, 0.85); c.set_line_width(10); c.stroke()
    if kind == 'lion':                                                     # mane behind head
        for k in range(12):
            a_ = k / 12 * 2 * math.pi; c.arc(hx + math.cos(a_) * hr, hy + math.sin(a_) * hr, hr * 0.38, 0, 2 * math.pi); fs(c, rgb('#9c5a1e'), 4)
    c.arc(hx, hy, hr, 0, 2 * math.pi); fs(c, b, 5)
    if kind in ('dog', 'wolf', 'horse', 'cow', 'deer', 'bear', 'lion'):     # snout
        c.save(); c.translate(hx + hr * 0.8, hy + hr * 0.25); c.scale(1.0, 0.75); c.arc(0, 0, hr * 0.5, 0, 2 * math.pi); c.restore(); fs(c, b2, 4)
        c.arc(hx + hr * 1.2, hy + hr * 0.1, 7, 0, 2 * math.pi); fill(c, INK)
    if kind in ('cat', 'wolf', 'dog', 'deer', 'horse', 'lion'):           # ears
        for ex in (-0.5, 0.15):
            poly(c, [(hx + ex * hr, hy - hr * 0.7), (hx + (ex + 0.25) * hr, hy - hr * 1.35), (hx + (ex + 0.5) * hr, hy - hr * 0.7)]); fs(c, b, 4)
    if kind in ('bear', 'cow'):
        for ex in (-0.6, 0.4): c.arc(hx + ex * hr, hy - hr * 0.8, hr * 0.28, 0, 2 * math.pi); fs(c, b, 4)
    if kind in ('elephant', 'mammoth'):
        c.save(); c.translate(hx - hr * 0.8, hy + 5); c.scale(0.6, 1); c.arc(0, 0, hr * 0.9, 0, 2 * math.pi); c.restore(); fs(c, b2, 4)
    if kind == 'deer':
        for ex in (-0.2, 0.3):
            line(c, hx + ex * hr, hy - hr, hx + ex * hr - 10, hy - hr - 70, 8, rgb('#8a6a3a'))
            line(c, hx + ex * hr - 6, hy - hr - 40, hx + ex * hr + 22, hy - hr - 62, 7, rgb('#8a6a3a'))
    if blink: line(c, hx + hr * 0.25, hy - hr * 0.15, hx + hr * 0.5, hy - hr * 0.15, 4)
    else: c.arc(hx + hr * 0.38, hy - hr * 0.15, 7, 0, 2 * math.pi); fill(c, INK)
    if mouth > 0.08:
        c.arc(hx + hr * 0.95, hy + hr * 0.45, 9 + 8 * mouth, 0, 2 * math.pi); fs(c, rgb('#6b1f1f'), 3)
    c.restore()

# ------------------------------------------------------------------ props & info graphics
def label_tag(c, x, y, label, k, rot=-0.12, col='#f4d35e', size=84, w=190):
    """pop-in tag for KEY NUMBERS. k = back((tg - t_pop)/0.45)"""
    if k <= 0: return
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k)
    tw = max(w, text_width(c, label, size) + 80)
    rr(c, -tw / 2, -55, tw, 110, 16); fs(c, rgb(col), 6)
    c.arc(-tw / 2 + 25, -30, 9, 0, 2 * math.pi); fs(c, (1, 1, 1), 4)
    text(c, label, 8, 26, size, INK); c.restore()

def calendar(c, x, y, top, big, s=1.0):
    c.save(); c.translate(x, y); c.scale(s, s)
    rr(c, -80, -95, 160, 190, 10); fs(c, (0.98, 0.97, 0.94), 5)
    c.rectangle(-80, -95, 160, 50); fill(c, rgb('#c8312c'))
    rr(c, -80, -95, 160, 190, 10); c.set_source_rgb(*INK); c.set_line_width(5); c.stroke()
    text(c, top, 0, -58, 34, (1, 1, 1)); text(c, big, 0, 55, 76 if len(big) <= 4 else 52, INK); c.restore()

def wall_clock(c, x, y, r, hours):
    c.arc(x, y, r, 0, 2 * math.pi); fs(c, (0.98, 0.97, 0.94), 5)
    for k in range(12):
        a = k / 12 * 2 * math.pi; line(c, x + math.cos(a) * r * 0.8, y + math.sin(a) * r * 0.8, x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9, 3)
    a1 = (hours % 12) / 12 * 2 * math.pi - math.pi / 2; a2 = (hours % 1) * 2 * math.pi - math.pi / 2
    line(c, x, y, x + math.cos(a1) * r * 0.5, y + math.sin(a1) * r * 0.5, 6); line(c, x, y, x + math.cos(a2) * r * 0.75, y + math.sin(a2) * r * 0.75, 4)

def coin(c, x, y, r, label, a=1.0, col='#c9c3b6'):
    c.save(); c.translate(x, y); glow(c, 0, 0, r * 2.2, rgb('#ffe9a8'), 0.35 * a)
    c.arc(0, 0, r, 0, 2 * math.pi); fs(c, rgb(col), 6, a)
    c.arc(0, 0, r * 0.8, 0, 2 * math.pi); c.set_source_rgba(*INK, 0.5 * a); c.set_line_width(3); c.stroke()
    text(c, label, 0, r * 0.3, r * (0.9 if len(label) <= 2 else 0.62), INK, a=a); c.restore()

def stamp(c, x, y, label, k, rot=-0.2, col='#d62f2f', size=150):
    """slam-in stamp. k = (tg - t_hit)/0.25. Pair with a SHAKE at t_hit."""
    if k <= 0: return
    sc = 1 + 1.6 * (1 - ease(k)); a = min(1, k * 3)
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(sc, sc)
    tw = text_width(c, label, size) + 120
    rr(c, -tw / 2, -95, tw, 190, 18); c.set_source_rgba(*rgb(col), a); c.set_line_width(14); c.stroke()
    text(c, label, 0, 52, size, rgb(col), a=a); c.restore()

def document(c, x, y, w, h, title, lines_, highlight=None, hk=0.0, rot=0.0, paper='#f3ead2'):
    """paper doc / board / newspaper. highlight=index of line to marker-swipe, hk=0..1"""
    c.save(); c.translate(x, y); c.rotate(rot)
    rr(c, -w / 2, -h / 2, w, h, 6); fs(c, rgb(paper), 5)
    text(c, title, 0, -h / 2 + 70, 54, INK)
    line(c, -w / 2 + 40, -h / 2 + 90, w / 2 - 40, -h / 2 + 90, 3)
    for i, s in enumerate(lines_):
        yy = -h / 2 + 160 + i * 75
        if highlight == i and hk > 0:
            c.rectangle(-w / 2 + 36, yy - 46, (w - 72) * hk, 60); fill(c, rgb('#f4e04d'), 0.75)
        text(c, s, -w / 2 + 50, yy, 44, INK, align='l')
    c.restore()

def bar_chart(c, x, y, w, h, values, labels, k, cols=None, title=None, fmt=str):
    """hand-drawn bars that grow with k (0..1). Put it INSIDE a scene (board, TV, wall), not on blank paper."""
    n = len(values); mx = max(values) or 1; bw = w / (n * 1.6)
    if title: text(c, title, x + w / 2, y - h - 30, 54, INK)
    line(c, x, y, x + w, y, 5); line(c, x, y, x, y - h, 5)
    for i, v in enumerate(values):
        kk = ease(k * n - i * 0.6)
        bh = h * 0.9 * v / mx * kk; bx = x + bw * 0.6 + i * bw * 1.6
        c.rectangle(bx, y - bh, bw, bh); fs(c, rgb((cols or ['#4f7cac'])[i % len(cols or ['#4f7cac'])]), 4)
        if kk > 0.95: text(c, fmt(v), bx + bw / 2, y - bh - 16, 40, INK)
        text(c, labels[i], bx + bw / 2, y + 46, 36, INK)

def lower_label(c, s, a=1.0):
    """place/date or name label, bottom-left, screen space. Fade it in ~0.5s, out after ~2.5s."""
    if a <= 0: return
    c.save(); screen(c)
    rr(c, 60, H - 140, 70 + text_width(c, s, 44), 70, 8); c.set_source_rgba(0.06, 0.06, 0.08, 0.82 * a); c.fill()
    c.rectangle(60, H - 140, 10, 70); c.set_source_rgba(*rgb('#f4d35e'), a); c.fill()
    text(c, s, 90, H - 92, 44, (1, 1, 1), align='l', a=a); c.restore()

def typed_card(c, t, lines_, col=(1, 1, 1)):
    """BLACK TEXT CARD. lines_: [(text, t_start, t_end, y, size, colour?)] — typed in sync with the narrator."""
    c.save(); screen(c); c.set_source_rgb(0, 0, 0); c.paint(); c.restore()
    for row in lines_:
        s, t0, t1, y, size = row[:5]; colr = row[5] if len(row) > 5 else col
        if t < t0: continue
        n = int(len(s) * clamp((t - t0) / max(0.01, t1 - t0)) + 0.999)
        full = text_width(c, s, size)
        text(c, s[:n], W / 2 - full / 2, y, size, colr, align='l')

def title_card(c, t, s, t0):
    """chapter title card (centred, fades in)."""
    c.save(); screen(c); c.set_source_rgb(0, 0, 0); c.paint(); c.restore()
    k = ease((t - t0) / 0.5); text(c, s, W / 2, H / 2 + 30, 110, (1, 1, 1), a=k)

# ------------------------------------------------------------------ ambient motion (use 1-3 per scene)
def dust(c, t, x0, y0, w, h, n=40, seed=3, col=(1, 0.9, 0.7), a=0.35):
    r_ = np.random.default_rng(seed)
    px, py, sp, sz = r_.uniform(0, 1, n), r_.uniform(0, 1, n), r_.uniform(0.2, 1, n), r_.uniform(1.5, 4, n)
    for i in range(n):
        xx = x0 + ((px[i] + 0.01 * t * sp[i]) % 1) * w + 12 * math.sin(t * sp[i] + i)
        yy = y0 + ((py[i] - 0.02 * t * sp[i]) % 1) * h
        c.arc(xx, yy, sz[i], 0, 2 * math.pi); c.set_source_rgba(*col, a * (0.5 + 0.5 * math.sin(t * 2 + i))); c.fill()

def steam(c, t, x, y, k=1.0):
    for j in range(3):
        ph = (t * 0.6 + j / 3) % 1
        c.move_to(x + (j - 1) * 14, y - ph * 110)
        for q in range(1, 6): c.line_to(x + (j - 1) * 14 + 10 * math.sin(t * 3 + q + j), y - ph * 110 - q * 14)
        c.set_source_rgba(1, 1, 1, 0.35 * (1 - ph) * k); c.set_line_width(6); c.stroke()

def rain(c, t, n=160, seed=4, a=0.35):
    r_ = np.random.default_rng(seed); px, py = r_.uniform(-200, W + 200, n), r_.uniform(0, H, n)
    for i in range(n):
        yy = (py[i] + t * 1400) % (H + 100) - 50; xx = px[i] - (yy * 0.15)
        line(c, xx, yy, xx - 8, yy + 34, 2, (0.8, 0.85, 1), a)

def snow(c, t, n=120, seed=6):
    r_ = np.random.default_rng(seed); px, py, sz = r_.uniform(0, W, n), r_.uniform(0, H, n), r_.uniform(2, 6, n)
    for i in range(n):
        yy = (py[i] + t * 60 * (sz[i] / 4)) % H; xx = px[i] + 20 * math.sin(t + i)
        c.arc(xx, yy, sz[i], 0, 2 * math.pi); fill(c, (1, 1, 1), 0.7)

def fire(c, t, x, y, s=1.0):
    glow(c, x, y - 40 * s, 260 * s, rgb('#ff9a3c'), 0.45 + 0.1 * math.sin(t * 17))
    for k, (col, sc) in enumerate((('#e8492c', 1.0), ('#f59a2c', 0.7), ('#ffe08a', 0.4))):
        fl = 1 + 0.12 * math.sin(t * 13 + k * 2)
        c.move_to(x - 50 * s * sc, y); c.curve_to(x - 60 * s * sc, y - 80 * s * sc * fl, x - 5, y - 120 * s * sc * fl, x, y - 170 * s * sc * fl)
        c.curve_to(x + 5, y - 120 * s * sc * fl, x + 60 * s * sc, y - 80 * s * sc * fl, x + 50 * s * sc, y); c.close_path()
        fs(c, rgb(col), 4 if k == 0 else 0.01)

def flicker(t, seed=0): return 0.85 + 0.15 * math.sin(t * 13 + seed) * math.sin(t * 7 + seed * 2)

def city_windows(c, x, y, w, h, seed=1, col='#ffd27a', a=0.7):
    for yy in range(int(y + 30), int(y + h - 20), 50):
        for xx in range(int(x + 20), int(x + w - 30), 44):
            if (xx * 7 + yy * 3 + seed) % 5 < 2: c.rectangle(xx, yy, 18, 24); fill(c, rgb(col), a)

# ------------------------------------------------------------------ timeline / scenes / render
class Scene:
    """
    name, start, end (seconds on the final timeline)
    draw(c, t, tg)  t = time inside scene, tg = global time
    shots: [(t0, t1, (cx,cy,z) from, (cx,cy,z) to, easing)] in GLOBAL seconds. Each new entry = a hard cut.
    enter: 'cut' | 'fade' (from black)    exit: 'cut' | 'zoom' (last shot zooms in, dissolve to black) | 'whip'
    """
    def __init__(self, name, start, end, draw, shots, enter='cut', exit='cut'):
        self.name, self.start, self.end, self.draw, self.shots = name, start, end, draw, shots
        self.enter, self.exit = enter, exit

SHAKES = []          # [(t_hit, amplitude_px)] global time. 5-10 small, 20-30 big.

def camera_at(sc, tg):
    shots = sc.shots or [(sc.start, sc.end, (W / 2, H / 2, 1.0), (W / 2, H / 2, 1.04), smooth)]
    cur = shots[-1]
    for s in shots:
        if s[0] <= tg < s[1]: cur = s; break
    a, b, p0, p1, fn = cur
    k = fn((tg - a) / max(1e-6, b - a))
    cx, cy, z = (lerp(p0[i], p1[i], k) for i in range(3))
    sx = sy = 0.0
    for t0, amp in SHAKES:
        if 0 <= tg - t0 < 0.6:
            d = math.exp(-(tg - t0) / 0.14); sx += amp * d * math.sin((tg - t0) * 75); sy += amp * d * math.cos((tg - t0) * 61)
    return [cx, cy, z, sx, sy]

def _render_scene(sc, tg):
    global TNOW
    TNOW = tg; CAM[:] = camera_at(sc, tg)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf)
    c.set_source_rgb(0, 0, 0); c.paint()
    sc.draw(c, tg - sc.start, tg); c.identity_matrix()
    return surf, c

def frame(scenes, tg, end):
    i = next((k for k, s in enumerate(scenes) if s.start <= tg < s.end), len(scenes) - 1)
    sc = scenes[i]; t = tg - sc.start
    nxt = scenes[i + 1] if i + 1 < len(scenes) else None
    prv = scenes[i - 1] if i > 0 else None
    whip_out = sc.exit == 'whip' and nxt and tg > sc.end - 0.3
    whip_in = prv is not None and prv.exit == 'whip' and t < 0.2
    if whip_out or whip_in:                    # motion-blurred whip pan across the cut
        k = 14; buf = np.zeros((H, W, 4), dtype=np.float32)
        for j in range(k):
            ts = tg + (j / k - 0.5) / FPS * 2.2
            s2 = sc if ts >= sc.start and ts < sc.end else (nxt if ts >= sc.end else prv)
            if whip_out and ts < sc.end: s2 = sc
            sub, _ = _render_scene(s2, ts); sub.flush()
            buf += np.ndarray((H, W, 4), np.uint8, sub.get_data()).astype(np.float32)
        out = (buf / k).astype(np.uint8)
        surf = cairo.ImageSurface.create_for_data(out, cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf)
    else:
        surf, c = _render_scene(sc, tg)
    if OVERLAY: c.identity_matrix(); OVERLAY(c, tg)   # captions etc. drawn sharp, after any whip blur
    if sc.enter == 'fade' and t < 0.14: c.set_source_rgba(0, 0, 0, 1 - t / 0.14); c.paint()
    if sc.exit == 'zoom' and tg > sc.end - 0.16: c.set_source_rgba(0, 0, 0, clamp((tg - (sc.end - 0.16)) / 0.16)); c.paint()
    if END_FADE and tg > end - 0.6: c.set_source_rgba(0, 0, 0, clamp((tg - (end - 0.6)) / 0.6)); c.paint()
    c.set_operator(cairo.OPERATOR_OVERLAY); c.set_source_surface(GRAIN, 0, 0); c.paint_with_alpha(0.06)
    c.set_operator(cairo.OPERATOR_OVER); surf.flush()
    return surf

def whip_shot(t0, t1, frm, dx=1600):
    """last shot of a scene with exit='whip': camera slams sideways."""
    return (t0, t1, frm, (frm[0] + dx, frm[1], frm[2]), ease_in)

def zoom_shot(t0, t1, target, z_end=7.5):
    """last shot of a scene with exit='zoom': camera dives into target (x,y,z_start)."""
    return (t0, t1, target, (target[0], target[1], z_end), ease_in)

def stills(scenes, end, times, path_fmt='/tmp/still_{:06.2f}.png'):
    out = []
    for ts in times:
        p = path_fmt.format(ts); frame(scenes, ts, end).write_to_png(p); out.append(p)
    return out

def render(scenes, end, out_path, t_from=0.0, t_to=None, preset='veryfast'):
    """Render [t_from, t_to) to an MP4 (no audio). Long videos: render chapters in parallel processes, then concat."""
    t_to = end if t_to is None else t_to
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', preset, '-crf', '18',
                          '-pix_fmt', 'yuv420p', out_path], stdin=subprocess.PIPE)
    for i in range(int(round(t_from * FPS)), int(round(t_to * FPS))):
        s = frame(scenes, i / FPS, end); p.stdin.write(bytes(s.get_data()))
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ sound design (synthesised, royalty-free)
SR = 44100
def _env(n, a=0.005, d=0.2): x = np.arange(n) / SR; return np.minimum(1, x / a) * np.exp(-x / d)
def sfx_pop(): n = int(0.12 * SR); x = np.arange(n) / SR; return np.sin(2 * np.pi * (900 - 3000 * x) * x) * _env(n, 0.002, 0.03) * 0.35
def sfx_ding(f=1800): n = int(0.8 * SR); x = np.arange(n) / SR; return (np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 2.7 * x)) * _env(n, 0.002, 0.18) * 0.18
def sfx_thud():
    n = int(0.5 * SR); x = np.arange(n) / SR; r = np.random.default_rng(1)
    return (np.sin(2 * np.pi * (90 - 60 * x) * x) * 0.8 + r.normal(0, 0.3, n) * np.exp(-x / 0.03)) * _env(n, 0.002, 0.12) * 0.6
def sfx_tick(): n = int(0.03 * SR); return np.random.default_rng(2).normal(0, 1, n) * _env(n, 0.001, 0.006) * 0.12
def sfx_whoosh():
    n = int(0.45 * SR); x = np.arange(n) / SR; r = np.random.default_rng(3).normal(0, 1, n)
    k = np.sin(np.pi * x / x[-1]) ** 2; sm = np.convolve(r, np.ones(40) / 40, 'same'); return sm * k * 0.9

def music_bed(duration, chords=None, bpm=80, seed=0, mood='tense'):
    """Ambient pad + soft pulse. Change chords/bpm per video so no two beds are identical.
    mood presets: tense, warm, mystery, epic, sad."""
    presets = {'tense': [[110, 130.8, 164.8], [98, 123.5, 146.8], [87.3, 110, 130.8], [98, 123.5, 146.8]],
               'warm': [[130.8, 164.8, 196], [110, 138.6, 164.8], [116.5, 146.8, 174.6], [98, 123.5, 146.8]],
               'mystery': [[110, 130.8, 155.6], [103.8, 123.5, 155.6], [98, 116.5, 146.8], [92.5, 110, 138.6]],
               'epic': [[73.4, 110, 146.8], [65.4, 98, 130.8], [87.3, 130.8, 174.6], [82.4, 123.5, 164.8]],
               'sad': [[110, 130.8, 164.8], [87.3, 110, 130.8], [130.8, 164.8, 196], [98, 123.5, 146.8]]}
    chords = chords or presets[mood]
    r = np.random.default_rng(seed); detune = 1 + r.uniform(-0.03, 0.03)
    N = int(duration * SR); mix = np.zeros(N)
    seg = 8 * 60 / bpm                             # one chord every 8 beats (6 s at 80 bpm), looping the progression
    for i in range(int(math.ceil(duration / seg))):
        ch = chords[i % len(chords)]
        a = int(i * seg * SR); b = min(N, int((i + 1) * seg * SR) + SR)
        if a >= N: break
        x = np.arange(b - a) / SR; w = np.sin(np.pi * np.clip(x / ((b - a) / SR), 0, 1)) ** 0.6
        for f in ch: f *= detune; mix[a:b] += 0.025 * w * (np.sin(2 * np.pi * f * x) + 0.4 * np.sin(2 * np.pi * 2 * f * x + 0.3))
    beat = 60 / bpm
    for k in np.arange(0, duration, beat):
        i = int(k * SR); n = int(0.35 * SR)
        if i + n < N: mix[i:i + n] += 0.06 * np.sin(2 * np.pi * 55 * detune * np.arange(n) / SR) * _env(n, 0.004, 0.09)
    return mix

def write_wav(path, sig):
    import wave
    sig = sig / max(1e-9, np.abs(sig).max()) * 0.5
    w = wave.open(path, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((sig * 32767).astype(np.int16).tobytes()); w.close()

def build_bed(duration, events, path, mood='tense', seed=0, bpm=80):
    """events: [(time, 'pop'|'ding'|'thud'|'tick'|'whoosh', gain)] -> music+SFX wav"""
    mix = music_bed(duration, mood=mood, seed=seed, bpm=bpm)
    lib = {'pop': sfx_pop, 'ding': sfx_ding, 'thud': sfx_thud, 'tick': sfx_tick, 'whoosh': sfx_whoosh}
    for tm, kind, g in events:
        s = lib[kind](); i = int(tm * SR); n = min(len(s), len(mix) - i)
        if n > 0: mix[i:i + n] += g * s[:n]
    write_wav(path, mix)
