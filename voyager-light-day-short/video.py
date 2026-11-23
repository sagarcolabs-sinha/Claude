"""Voyager 1: one light-day from Earth — a 41 s vertical Short built for retention.

Usage:
  python video.py stills OUT_DIR t1 t2 ...      # PNG stills at given times
  python video.py render OUT.mp4 T_FROM T_TO    # silent video chunk
  python video.py bed OUT.wav                   # music + SFX bed
Needs timeline.json (from assemble_vo.py) next to this file or at $TIMELINE.
"""
import os, sys, json, math
import numpy as np
import engine as E
from engine import *

E.END_FADE = False                      # seamless loop back to the first frame
HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.environ.get('TIMELINE', os.path.join(HERE, 'timeline.json'))))
END = round(TL['duration'] + 0.12, 2)
LINE = {L['id']: L for L in TL['lines']}

def W_(line_id, word, n=0):
    """start time of the n-th occurrence of `word` in a voice line"""
    hits = [w for w in LINE[line_id]['words'] if w[0].strip(',.:').lower() == word.lower()]
    return hits[n][1]

def span(line_id): return (LINE[line_id]['start'], LINE[line_id]['end'])

# ------------------------------------------------------------------ shared drawing
_sr = np.random.default_rng(1977)
STARS = np.c_[_sr.uniform(-900, W + 900, 420), _sr.uniform(-900, H + 900, 420),
              _sr.uniform(1.2, 4.2, 420), _sr.uniform(0, 6.3, 420)]

def starfield(c, t, a=1.0, tint=(1, 1, 1)):
    for x, y, r, ph in STARS:
        k = 0.55 + 0.45 * math.sin(t * 2.3 + ph)
        c.arc(x, y, r, 0, 2 * math.pi); c.set_source_rgba(*tint, a * k); c.fill()

def space_bg(c, t, top='#0b1030', bot='#03040c', neb=None):
    cam(c, 0.45)
    vgrad(c, -900, -900, W + 1800, H + 1800, rgb(top), rgb(bot))
    if neb: glow(c, W * 0.7, H * 0.3, 900, rgb(neb), 0.25)
    starfield(c, t)

def voyager(c, x, y, s=1.0, rot=0.0, t=0.0, tint=None):
    """the probe in house style: dish, gold bus, three booms, blinking light"""
    c.save(); c.translate(x, y); c.rotate(rot + 0.04 * math.sin(t * 0.7)); c.scale(s, s)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    line(c, 30, 70, 560, -330, 12); line(c, 30, 70, 560, -330, 5, rgb('#9aa3ad'))          # magnetometer boom
    for k in (0.55, 0.8, 1.0):
        bx, by = 30 + 530 * k, 70 - 400 * k; c.arc(bx, by, 10, 0, 2 * math.pi); fs(c, rgb('#d8dde3'), 4)
    line(c, -30, 90, -330, 300, 16); line(c, -30, 90, -330, 300, 8, rgb('#6c717a'))         # RTG boom
    for k in range(3):
        cx_, cy_ = -170 - k * 62, 190 + k * 44
        c.save(); c.translate(cx_, cy_); c.rotate(0.61)
        rr(c, -34, -26, 68, 52, 10); fs(c, rgb('#4a4e57'), 5)
        for f in (-18, 0, 18): line(c, f, -38, f, 38, 4)
        c.restore()
    line(c, 40, 100, 270, 260, 16); line(c, 40, 100, 270, 260, 8, rgb('#6c717a'))          # science boom
    rr(c, 220, 220, 120, 80, 10); fs(c, rgb('#8a8f98'), 5)
    rr(c, 300, 200, 70, 40, 8); fs(c, rgb('#2b2f36'), 4)
    pts = [(math.cos(k / 10 * 2 * math.pi) * 92, 110 + math.sin(k / 10 * 2 * math.pi) * 52) for k in range(10)]
    poly(c, pts); fs(c, rgb('#c9a227'), 6)                                                 # gold foil bus
    for k in range(0, 10, 2): line(c, 0, 110, *pts[k], 2, rgb('#8c6d12'), 0.6)
    c.save(); c.scale(1, 0.94); c.arc(0, -10, 235, 0, 2 * math.pi); c.restore()          # the dish
    g = cairo.RadialGradient(-60, -70, 20, 0, -10, 250)
    g.add_color_stop_rgb(0, 1, 0.99, 0.95); g.add_color_stop_rgb(1, *rgb('#b9b2a0'))
    c.set_source(g); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
    for r_ in (160, 80):
        c.save(); c.scale(1, 0.94); c.arc(0, -10, r_, 0, 2 * math.pi); c.restore()
        c.set_source_rgba(*INK, 0.25); c.set_line_width(3); c.stroke()
    for a_ in (-2.3, -0.8, 1.6):
        line(c, math.cos(a_) * 200, -10 + math.sin(a_) * 188, 0, -10, 5)
    c.arc(0, -10, 26, 0, 2 * math.pi); fs(c, rgb('#d8dde3'), 5)
    on = (t % 1.4) < 0.25
    c.arc(80, 150, 11, 0, 2 * math.pi); fs(c, rgb('#ff4b4b') if on else rgb('#5a1d1d'), 3)
    if on: glow(c, 80, 150, 50, rgb('#ff4b4b'), 0.6)
    if tint:
        c.save(); c.scale(1, 0.94); c.arc(0, -10, 236, 0, 2 * math.pi); c.restore(); fill(c, rgb(tint), 0.22)
    c.restore()

def earth(c, x, y, r):
    glow(c, x, y, r * 2.6, rgb('#5fa8ff'), 0.45)
    c.arc(x, y, r, 0, 2 * math.pi); fs(c, rgb('#2f6fd1'), max(3, r * 0.06))
    c.save(); c.arc(x, y, r, 0, 2 * math.pi); c.clip()
    for dx, dy, rx, ry in ((-0.35, -0.2, 0.42, 0.3), (0.3, 0.35, 0.35, 0.22), (0.45, -0.45, 0.2, 0.15)):
        c.save(); c.translate(x + dx * r, y + dy * r); c.scale(rx * r, ry * r); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
        fill(c, rgb('#4caf50'))
    c.restore()

def top_label(c, s, a=1.0, y=230):
    """place/date label near the TOP (the bottom is covered by the Shorts UI)"""
    if a <= 0: return
    c.save(); screen(c); tw = text_width(c, s, 60) + 70
    rr(c, W / 2 - tw / 2, y - 62, tw, 86, 14); c.set_source_rgba(0.05, 0.05, 0.08, 0.85 * a); c.fill()
    c.rectangle(W / 2 - tw / 2, y - 62, 12, 86); c.set_source_rgba(*rgb('#f4d35e'), a); c.fill()
    text(c, s, W / 2 + 6, y, 60, (1, 1, 1), a=a); c.restore()

def phone_body(c, x, y, w, h, draw_screen, t):
    rr(c, x - w / 2, y - h / 2, w, h, 70); fs(c, rgb('#1d1f26'), 9)
    sx, sy, sw, sh = x - w / 2 + 26, y - h / 2 + 26, w - 52, h - 52
    c.save(); rr(c, sx, sy, sw, sh, 50); c.clip()
    c.set_source_rgb(*rgb('#f4f1ea')); c.paint(); draw_screen(c, sx, sy, sw, sh, t); c.restore()
    rr(c, x - 70, y - h / 2 + 40, 140, 30, 15); fill(c, rgb('#1d1f26'))

def chat_screen(bubble, sent_at, status_fn, draft=None):
    def draw(c, sx, sy, sw, sh, tg):
        c.rectangle(sx, sy, sw, 230); fill(c, rgb('#22335c'))
        c.arc(sx + 110, sy + 150, 52, 0, 2 * math.pi); fs(c, rgb('#0b1030'), 4)
        c.save(); c.arc(sx + 110, sy + 150, 50, 0, 2 * math.pi); c.clip()
        voyager(c, sx + 112, sy + 150, 0.16, t=tg); c.restore()
        text(c, 'Voyager 1', sx + 190, sy + 150, 64, (1, 1, 1), align='l')
        text(c, '1 light-day away', sx + 192, sy + 200, 40, rgb('#a9b8dc'), align='l', bold=False)
        if bubble and tg >= sent_at:
            k = back((tg - sent_at) / 0.35)
            bw = text_width(c, bubble, 70) + 90
            c.save(); c.translate(sx + sw - 40 - bw / 2, sy + 420); c.scale(k, k)
            rr(c, -bw / 2, -65, bw, 130, 50); fs(c, rgb('#3a86ff'), 5)
            text(c, bubble, 0, 24, 70, (1, 1, 1)); c.restore()
            st = status_fn(tg)
            if st: text(c, st[0], sx + sw - 50, sy + 545, st[2] if len(st) > 2 else 46, rgb(st[1]), align='r')
        if draft is not None:
            rr(c, sx + 30, sy + sh - 170, sw - 60, 110, 55); fs(c, (1, 1, 1), 4)
            n = int(len(draft[0]) * clamp((tg - draft[1]) / max(0.01, draft[2] - draft[1])) + 0.999)
            text(c, draft[0][:n], sx + 70, sy + sh - 95, 60, INK, align='l')
            pressed = tg >= draft[3]
            c.arc(sx + sw - 100, sy + sh - 115, 46 * (0.85 if pressed else 1), 0, 2 * math.pi)
            fs(c, rgb('#2ec27e') if pressed else rgb('#3a86ff'), 4)
            poly(c, [(sx + sw - 118, sy + sh - 138), (sx + sw - 76, sy + sh - 115), (sx + sw - 118, sy + sh - 92)]); fill(c, (1, 1, 1))
    return draw

def bedroom(c, t):
    cam(c, 0.6)
    vgrad(c, -600, -600, W + 1200, H + 1200, rgb('#1d2747'), rgb('#0d1224'))
    rr(c, 560, 260, 420, 560, 10); fs(c, rgb('#0a0e22'), 10)
    c.save(); rr(c, 560, 260, 420, 560, 10); c.clip(); starfield(c, t * 0.5, 0.9); c.restore()
    line(c, 770, 260, 770, 820, 10); line(c, 560, 540, 980, 540, 10)
    c.arc(680, 360, 46, 0, 2 * math.pi); fs(c, rgb('#f6efc4'), 4)
    cam(c, 1.0)
    c.rectangle(-600, 1500, W + 1200, 900); fill(c, rgb('#2a2433'))
    rr(c, -200, 1240, 900, 300, 30); fs(c, rgb('#5b4b8a'), 6)                         # bed
    rr(c, -160, 1170, 330, 120, 40); fs(c, rgb('#e8e2f4'), 5)                         # pillow
    rr(c, 860, 1080, 60, 420, 8); fs(c, rgb('#3a3140'), 5)                            # lamp stand
    poly(c, [(800, 1080), (980, 1080), (940, 960), (840, 960)]); fs(c, rgb('#f3c977'), 5)
    glow(c, 890, 1020, 520, rgb('#ffcf87'), 0.32 * flicker(t, 2))

def small_phone(c, hx, hy):
    rr(c, hx - 34, hy - 70, 68, 120, 12); fs(c, rgb('#1d1f26'), 4)
    rr(c, hx - 26, hy - 62, 52, 96, 8); fill(c, rgb('#9cc4ff')); glow(c, hx, hy - 20, 140, rgb('#9cc4ff'), 0.35)

# ------------------------------------------------------------------ scenes
def s_open(c, t, tg):
    space_bg(c, tg)
    cam(c, 0.8); earth(c, 260, 1560, 16)
    text(c, 'EARTH', 260, 1515, 46, rgb('#a9c8ff'), a=smooth((tg - 1.0) / 0.4))
    cam(c, 1.0); voyager(c, 560, 820, 0.95, -0.1, tg)

def s_phone_hook(c, t, tg):
    bedroom(c, tg)
    cam(c, 1.0)
    t_msg, t_today, t_arr, t_tom = W_('hook', 'message'), W_('hook', 'today'), W_('hook', 'arrives'), W_('hook', 'tomorrow')
    def status(tt):
        if tt < t_today: return ('sending...', '#8a8f98')
        if tt < t_arr: return ('sent: TODAY', '#8a8f98', 52)
        return ('arrives in ~24 hours', '#c8312c', 52)
    phone_body(c, 540, 1000, 760, 1340, chat_screen('good morning!', t_msg, status), tg)
    stamp(c, 560, 1180, 'TOMORROW', (tg - t_tom) / 0.25, rot=-0.14, size=120)

def s_map(c, t, tg):
    space_bg(c, tg)
    cam(c, 1.0)
    ex, ey, vx, vy = 540, 1840, 560, 560
    c.set_dash([22, 22]); line(c, ex, ey, vx, vy + 120, 5, (1, 1, 1), 0.45); c.set_dash([])
    t0 = W_('date', 'one'); k = clamp((tg - t0) / 1.6)
    if 0 < k < 1 or tg > t0:                                                   # a light pulse travels out
        px, py = lerp(ex, vx, (k * 0.999)), lerp(ey, vy + 120, k)
        glow(c, px, py, 90, rgb('#fff3a0'), 0.9); c.arc(px, py, 14, 0, 2 * math.pi); fill(c, rgb('#fffbe0'))
    earth(c, ex, ey, 70)
    voyager(c, vx, vy, 0.62, -0.12, tg)
    ta = t < 1.9
    if ta:
        kc = back((tg - W_('date', 'eighteenth')) / 0.4)
        if kc > 0.01: calendar(c, 300, 1000, 'NOV', '18', 1.6 * kc)
        if tg > W_('date', 'November'): text(c, '2026', 300, 830, 80, (1, 1, 1), a=smooth((tg - W_('date', 'November')) / 0.3))
    stamp(c, 560, 900, 'FIRST EVER', (tg - W_('date', 'first')) / 0.25, rot=-0.12, col='#f4d35e', size=110)
    label_tag(c, 540, 1330, '1 LIGHT-DAY', back((tg - W_('date', 'light-day')) / 0.45), rot=0.05, size=80)
    label_tag(c, 540, 1480, '16,000,000,000 MILES', back((tg - W_('miles', 'sixteen')) / 0.45), rot=-0.04, col='#ffffff', size=64)

def battery(c, x, y, s, level, tg):
    c.save(); c.translate(x, y); c.scale(s, s)
    rr(c, -130, -70, 260, 140, 22); fs(c, rgb('#1b1b22'), 9)
    rr(c, 130, -28, 26, 56, 8); fs(c, rgb('#1b1b22'), 6)
    on = (tg % 0.5) < 0.32
    rr(c, -112, -52, 224 * level, 104, 12); fill(c, rgb('#ff3b30') if on else rgb('#7a1d18'))
    text(c, '!', 0, 38, 110, (1, 1, 1)); c.restore()

def s_lowbat(c, t, tg):
    space_bg(c, tg, top='#2a0710', bot='#08020a', neb='#ff2a2a')
    cam(c, 1.0); voyager(c, 470, 900, 0.85, -0.1, tg, tint='#ff2a2a')
    tp = W_('loop', 'power')
    lvl = lerp(0.42, 0.12, smooth((tg - 12.2) / 1.0))
    kb = back((tg - 12.15) / 0.4)
    if kb > 0.01: battery(c, 760, 520, 1.5 * kb, lvl, tg)
    text(c, 'POWER', 760, 720, 90, rgb('#ff6b5b'), a=smooth((tg - tp) / 0.2))

def retro_computer(c, x, y, tg):
    rr(c, x - 230, y - 300, 460, 600, 16); fs(c, rgb('#d9cfb2'), 7)
    for k, rx in enumerate((x - 105, x + 105)):
        c.arc(rx, y - 150, 80, 0, 2 * math.pi); fs(c, rgb('#3a352c'), 5)
        c.arc(rx, y - 150, 26, 0, 2 * math.pi); fs(c, rgb('#d9cfb2'), 4)
        for j in range(3):
            a = tg * (3 if k else 2.2) + j * 2.09
            line(c, rx + math.cos(a) * 26, y - 150 + math.sin(a) * 26, rx + math.cos(a) * 70, y - 150 + math.sin(a) * 70, 5, rgb('#6b6455'))
    for i in range(12):
        on = int(tg * 7 + i * 5) % 4 == 0
        c.arc(x - 165 + (i % 6) * 66, y + 40 + (i // 6) * 60, 15, 0, 2 * math.pi)
        fs(c, rgb('#ff5a36') if on else rgb('#5a2a20'), 3)
    rr(c, x - 160, y + 170, 320, 70, 8); fs(c, rgb('#2b2a26'), 4)
    text(c, 'MEMORY: 70 KB', x, y + 222, 46, rgb('#7dff9b'))

def s_memory(c, t, tg):
    cam(c, 0.6)
    vgrad(c, -600, -600, W + 1200, H + 1200, rgb('#6b4a2a'), rgb('#2a1a10'))
    glow(c, 540, 400, 900, rgb('#ffcf87'), 0.3)
    cam(c, 1.0)
    rr(c, 90, 110, 900, 560, 18); fs(c, rgb('#24392e'), 10)                           # chalkboard
    t_mem = W_('memory', 'memory'); kb = clamp((tg - t_mem) / 1.1)
    text(c, 'MEMORY', 540, 185, 66, (1, 1, 1), a=smooth((tg - t_mem) / 0.3))
    line(c, 160, 610, 760, 610, 5, (1, 1, 1), 0.8)
    for i, (v, name, col) in enumerate(((70, 'VOYAGER', '#f4d35e'), (3000, '1 PHOTO', '#7ec8ff'))):
        bx = 210 + i * 300; bh = max(8, 300 * v / 3000 * ease(kb * 1.6 - i * 0.6)); kk = ease(kb * 1.6 - i * 0.6)
        if kb <= 0: continue
        c.rectangle(bx, 610 - bh, 200, bh); fs(c, rgb(col), 4)
        if kk > 0.9:
            text(c, f'{v:,} KB', bx + 100, 610 - bh - 16, 50, (1, 1, 1))
            text(c, name, bx + 100, 610 - bh - 66, 46, rgb(col))
    c.rectangle(-600, 1290, W + 1200, 900); fill(c, rgb('#3b2a1e'))
    rr(c, -100, 1240, 1300, 70, 10); fs(c, rgb('#7a5534'), 6)                         # desk
    retro_computer(c, 360, 940, tg)
    person(c, 820, 1270, 1.2, shirt='#c96f2f', pants='#5b3a1f', hair='#5a3a1c', style='curly', beard='stubble',
           glasses=True, blink=blinking(tg, 0.4), armL=0.5, mood='happy' if tg < t_mem else 'shocked')
    ky = back((tg - W_('memory', 'nineteen')) / 0.4)
    if tg < W_('memory', 'on') and ky > 0.01: calendar(c, 860, 720, 'YEAR', '1977', 1.1 * ky)
    if tg > W_('memory', 'photo'):
        k = back((tg - W_('memory', 'photo')) / 0.4)
        c.save(); c.translate(870, 460); c.scale(0.85 * k, 0.85 * k); c.rotate(0.12)
        rr(c, -70, -120, 140, 240, 18); fs(c, rgb('#1d1f26'), 5)
        c.rectangle(-55, -100, 110, 190); fill(c, rgb('#8fd3ff'))
        poly(c, [(-55, 90), (-10, 10), (20, 50), (55, -20), (55, 90)]); fill(c, rgb('#3f8f4f'))
        c.arc(30, -60, 18, 0, 2 * math.pi); fill(c, rgb('#ffd34d')); c.restore()

def s_fridge(c, t, tg):
    cam(c, 0.6); vgrad(c, -600, -600, W + 1200, H + 1200, rgb('#1a2233'), rgb('#0b0f18'))
    cam(c, 1.0)
    c.rectangle(-600, 1560, W + 1200, 900); fill(c, rgb('#262a33'))
    rr(c, 300, 420, 560, 1150, 26); fs(c, rgb('#f3f6f8'), 8)                         # fridge body
    rr(c, 330, 450, 500, 1090, 16); fill(c, rgb('#fff6d6'))
    glow(c, 580, 520, 700, rgb('#fff1b8'), 0.55)
    for yy in (780, 1050, 1320): line(c, 330, yy, 830, yy, 6, rgb('#c9d3dc'))
    c.arc(580, 500, 34, 0, 2 * math.pi); fs(c, rgb('#fffbe0'), 4)                    # bulb
    for jx, col in ((420, '#e85d4a'), (500, '#7cc06a')): rr(c, jx, 1180, 64, 130, 12); fs(c, rgb(col), 4)
    rr(c, 650, 1200, 150, 110, 14); fs(c, rgb('#f2d16b'), 4)
    voyager(c, 600, 700, 0.24, -0.1, tg)                                            # tiny probe on a shelf
    poly(c, [(300, 420), (60, 300), (60, 1700), (300, 1570)]); fs(c, rgb('#e4e9ee'), 8)  # open door
    person(c, 150, 1700, 1.15, shirt='#5c7fb5', pants='#8a8fb8', hair='#2a1d16', style='bob', armR=1.4,
           mood='shocked' if tg > W_('radio', 'weaker') else 'neutral', blink=blinking(tg, 1.2))
    label_tag(c, 590, 870, '~22 W RADIO', back((tg - W_('radio', 'weaker')) / 0.45), rot=-0.08, size=66)
    label_tag(c, 600, 380, 'BRIGHTER!', back((tg - W_('radio', 'bulb')) / 0.45), rot=0.06, col='#ffffff', size=50)

def s_dish(c, t, tg):
    space_bg(c, tg, top='#0d1640', bot='#1b1530')
    cam(c, 0.9)
    tf = W_('faint', 'billionth')
    ph = tg * 6
    c.move_to(540, -500)
    for i in range(1, 60):
        yy = -500 + i * 27; c.line_to(540 + 26 * math.sin(i * 0.9 - ph), yy)
    c.set_source_rgba(*rgb('#9ff0ff'), 0.55); c.set_line_width(5); c.stroke()
    cam(c, 1.0)
    c.rectangle(-900, 1450, W + 1800, 1200); fill(c, rgb('#3a2a24'))
    poly(c, [(440, 1460), (640, 1460), (590, 1180), (490, 1180)]); fs(c, rgb('#d8dde3'), 7)   # pedestal
    c.save(); c.translate(540, 1060); c.rotate(-0.12)
    c.save(); c.scale(1, 0.42); c.arc(0, 0, 400, 0, 2 * math.pi); c.restore(); fs(c, rgb('#eef1f4'), 8)
    c.save(); c.scale(1, 0.42); c.arc(0, 0, 250, 0, 2 * math.pi); c.restore(); c.set_source_rgba(*INK, 0.25); c.set_line_width(3); c.stroke()
    for a_ in (-2.6, -0.5): line(c, math.cos(a_) * 360, math.sin(a_) * 150, 0, -230, 6)
    line(c, 0, 60, 0, -230, 6); rr(c, -24, -270, 48, 60, 8); fs(c, rgb('#c9ced4'), 5)
    c.restore()
    hit = (tg * 2) % 1
    glow(c, 540, 830, 120 * (0.6 + hit), rgb('#9ff0ff'), 0.35 * (1 - hit))
    person(c, 760, 1500, 0.32, shirt='#c8312c', blink=blinking(tg, 0.3))
    label_tag(c, 540, 470, '0.000000000000000001 W', back((tg - tf) / 0.45), rot=-0.05, col='#9ff0ff', size=56)
    label_tag(c, 880, 1600, '70 m DISH', back((tg - W_('faint', 'Giant')) / 0.45), rot=0.08, size=56)

def power_chart(c, x, y, w, h, k):
    rr(c, x - 30, y - h - 90, w + 60, h + 160, 16); fs(c, rgb('#0d1b2a'), 8)
    text(c, 'POWER (W)', x + 10, y - h - 30, 46, rgb('#7dff9b'), align='l')
    line(c, x, y, x + w, y, 4, rgb('#7dff9b')); line(c, x, y, x, y - h + 40, 4, rgb('#7dff9b'))
    n = 40; pts = [(x + w * i / n, y - h + 60 + (h - 110) * (i / n) ** 1.05) for i in range(n + 1)]
    m = max(1, int(n * k))
    c.move_to(*pts[0])
    for p in pts[1:m + 1]: c.line_to(*p)
    c.set_source_rgb(*rgb('#ff6b5b')); c.set_line_width(8); c.stroke()

INSTR = [('CAMERAS', 'imaging'), ('INFRARED', 'iris'), ('ULTRAVIOLET', 'uvs'), ('COSMIC RAY', 'crs'), ('LECP', 'lecp'),
         ('MAGNETOMETER', 'mag'), ('PLASMA WAVE', 'pws')]

def switch_panel(c, x, y, tg, offs):
    rr(c, x - 420, y - 60, 840, 7 * 120 + 60, 22); fs(c, rgb('#3b4350'), 8)
    for i, (name, key) in enumerate(INSTR):
        yy = y + 30 + i * 120
        on = not (key in offs and tg >= offs[key])
        text(c, name, x - 380, yy + 18, 54, (1, 1, 1), align='l')
        rr(c, x + 140, yy - 36, 120, 72, 36); fs(c, rgb('#1d222a'), 5)
        kx = x + 224 if on else x + 176
        c.arc(kx, yy, 28, 0, 2 * math.pi); fs(c, rgb('#e6e9ee'), 4)
        c.arc(x + 340, yy, 26, 0, 2 * math.pi); fs(c, rgb('#38e07b') if on else rgb('#2a2f36'), 4)
        if on: glow(c, x + 340, yy, 70, rgb('#38e07b'), 0.5)

OFFS = {}
def s_control(c, t, tg):
    cam(c, 0.6); vgrad(c, -600, -600, W + 1200, H + 1200, rgb('#14213d'), rgb('#070b16'))
    cam(c, 1.0)
    c.rectangle(-600, 1560, W + 1200, 900); fill(c, rgb('#1a1f2b'))
    if t < 2.6:
        power_chart(c, 150, 860, 780, 560, clamp((tg - W_('power', 'power')) / 1.6))
        label_tag(c, 640, 560, '-4 W / YEAR', back((tg - W_('power', 'four')) / 0.45), rot=-0.06, size=74)
        c.rectangle(-600, 1250, W + 1200, 900); fill(c, rgb('#1a1f2b'))
        person(c, 540, 1300, 1.0, shirt='#5b6b8c', hair='#3b2a1a', style='short', glasses=True,
               blink=blinking(tg, 0.9), mood='worried', armR=-0.9)
    else:
        c.rectangle(-600, 1250, W + 1200, 900); fill(c, rgb('#1a1f2b'))
        c.save(); c.translate(640, 330); c.scale(0.72, 0.72); switch_panel(c, 0, 0, tg, OFFS); c.restore()
        two = W_('two', 'two')
        if tg > two:
            label_tag(c, 640, 200, '2 STILL ON', back((tg - two) / 0.45), rot=-0.05, col='#38e07b', size=84)
        sk0, sk1 = span('skit')
        if tg < two:
            person(c, 150, 1300, 1.05, shirt='#5b6b8c', hair='#3b2a1a', style='short', glasses=True,
                   blink=blinking(tg, 0.9), mood='worried', armR=-1.6 if tg < sk1 else -0.4,
                   mouth=talking(tg, (sk0, sk1)), headrot=-0.12 if sk0 <= tg <= sk1 else 0.0)

def s_drift(c, t, tg):
    space_bg(c, tg, top='#070a1c', bot='#000000')
    cam(c, 1.0)
    k = smooth(t / 2.7)
    voyager(c, lerp(560, 380, k), lerp(980, 620, k), lerp(0.75, 0.16, k), -0.1 + 0.25 * k, tg)

def s_goodbye(c, t, tg):
    if t < 1.85:
        bedroom(c, tg)
        cam(c, 1.0)
        person(c, 640, 1560, 1.3, shirt='#c8312c', pants='#2b2b33', hair='#2a1d16', style='short',
               armR=-1.25, prop=small_phone, blink=blinking(tg, 0.2), mood='worried')
    else:
        bedroom(c, tg)
        cam(c, 1.0)
        tr = W_('end', 'remember')
        phone_body(c, 540, 1000, 760, 1340,
                   chat_screen('good morning!', -99, lambda tt: ('delivered', '#2e9e5b'), draft=('goodbye, Voyager', tg - t + 1.85, tr - 0.1, tr + 0.05)), tg)

# ------------------------------------------------------------------ captions (word-by-word, yellow active word)
NUM = {'eighteenth,': '18TH', 'sixteen': '16', 'four': '4', 'two': '2', 'one': '1'}
def caption_words():
    out = []
    for L in TL['lines']:
        ws = L['words']; i = 0
        while i < len(ws):
            w, a, b = ws[i]
            if w.lower() == 'nineteen' and i + 1 < len(ws) and ws[i + 1][0].lower().startswith('seventy'):
                out.append(['1977,', a, ws[i + 1][2], L['id']]); i += 2; continue
            if L['id'] == 'date' and w.lower() == 'one': d = '1'
            elif L['id'] == 'end' and w.lower() == 'one': d = w
            else: d = NUM.get(w.lower(), w)
            out.append([d, a, b, L['id']]); i += 1
    return out

def caption_groups():
    groups, cur = [], []
    for w in caption_words():
        cur.append(w)
        txt = ' '.join(x[0] for x in cur)
        if w[0][-1] in ',.:?!' or len(cur) >= 3 or len(txt) > 15:
            groups.append(cur); cur = []
    if cur: groups.append(cur)
    res = []
    for i, g in enumerate(groups):
        t0 = g[0][1]; t1 = groups[i + 1][0][1] if i + 1 < len(groups) else g[-1][2] + 0.4
        if t1 - g[-1][2] > 0.35: t1 = g[-1][2] + 0.35
        res.append((0.0 if i == 0 else t0, t1, g))
    return res

GROUPS = caption_groups()
def captions(c, tg, y=1360):
    for t0, t1, g in GROUPS:
        if not (t0 <= tg < t1): continue
        words = [w[0].strip(',.:').upper() for w in g]
        size = 118
        c.save(); screen(c)
        c.select_font_face('Caveat', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
        sp = c.text_extents(' ').x_advance + 10
        widths = [c.text_extents(s).x_advance for s in words]
        total = sum(widths) + sp * (len(words) - 1)
        sc = min(1.0, 880 / total) * (0.85 + 0.15 * back((tg - t0) / 0.14))
        c.translate(W / 2, y); c.scale(sc, sc)
        x = -total / 2
        for s, wd, w in zip(words, widths, g):
            active = w[1] <= tg < w[2] + 0.05
            col = rgb('#ffd93b') if active else (1, 1, 1)
            if w[3] == 'skit': col = rgb('#8fe3ff')
            c.move_to(x, 0); c.text_path(s)
            c.set_source_rgb(0, 0, 0); c.set_line_width(16); c.set_line_join(cairo.LINE_JOIN_ROUND); c.stroke_preserve()
            c.set_source_rgb(*col); c.fill()
            x += wd + sp
        c.restore()

def with_captions(draw, vig=0.7):
    def d(c, t, tg):
        draw(c, t, tg); screen(c); vignette(c, vig)
    return d

# ------------------------------------------------------------------ edit (all times from the voice timeline)
T = {k: span(k) for k in LINE}
c_phone = W_('hook', 'a')
c_map = T['date'][0] - 0.03
c_bat = T['loop'][0] - 0.08
c_mem = T['memory'][0] - 0.06
c_fridge = T['radio'][0] - 0.08
c_dish = T['faint'][0] - 0.04
c_ctrl = T['power'][0] - 0.06
c_drift = T['end'][0] - 0.06
c_bye = W_('end', 'So')
OFFS.update({'imaging': W_('power', 'switching') - 0.15, 'iris': W_('power', 'switching') + 0.2,
             'uvs': W_('power', 'instruments'), 'crs': W_('power', 'instruments') + 0.4, 'lecp': T['skit'][1] - 0.2})

scenes = [
    Scene('open', 0, c_phone, with_captions(s_open),
          [(0, 1.0, (560, 850, 1.35), (560, 840, 1.45), smooth),
           (1.0, c_phone, (520, 1150, 0.95), (480, 1250, 0.72), ease)]),
    Scene('phone', c_phone, c_map, with_captions(s_phone_hook),
          [(c_phone, W_('hook', 'arrives'), (540, 960, 1.0), (540, 940, 1.07), smooth),
           (W_('hook', 'arrives'), c_map - 0.22, (540, 1150, 1.35), (545, 1160, 1.45), smooth),
           whip_shot(c_map - 0.22, c_map, (545, 1160, 1.45), 1400)], exit='whip'),
    Scene('map', c_map, c_bat, with_captions(s_map),
          [(c_map, W_('date', 'Voyager') - 0.05, (330, 960, 1.35), (320, 950, 1.45), smooth),
           (W_('date', 'Voyager') - 0.05, W_('date', 'one') - 0.1, (560, 800, 1.2), (560, 820, 1.32), smooth),
           (W_('date', 'one') - 0.1, T['miles'][0], (540, 1180, 0.88), (540, 1170, 0.95), smooth),
           (T['miles'][0], c_bat, (540, 1350, 1.2), (540, 1360, 1.32), smooth)]),
    Scene('lowbat', c_bat, c_mem, with_captions(s_lowbat, 0.85),
          [(c_bat, c_mem, (560, 760, 1.05), (580, 740, 1.18), smooth)]),
    Scene('memory', c_mem, c_fridge, with_captions(s_memory),
          [(c_mem, W_('memory', 'on'), (560, 900, 1.02), (580, 890, 1.1), smooth),
           (W_('memory', 'on'), W_('memory', 'photo') - 0.2, (540, 420, 1.3), (540, 420, 1.36), smooth),
           (W_('memory', 'photo') - 0.2, c_fridge - 0.22, (560, 420, 1.36), (580, 410, 1.45), smooth),
           whip_shot(c_fridge - 0.22, c_fridge, (580, 410, 1.45), 1400)], exit='whip'),
    Scene('fridge', c_fridge, c_dish, with_captions(s_fridge),
          [(c_fridge, W_('radio', 'weaker') - 0.1, (520, 1000, 1.0), (530, 990, 1.06), smooth),
           (W_('radio', 'weaker') - 0.1, c_dish, (590, 760, 1.4), (595, 750, 1.5), smooth)]),
    Scene('dish', c_dish, c_ctrl, with_captions(s_dish),
          [(c_dish, W_('faint', 'billionth') - 0.2, (540, 300, 1.2), (540, 560, 1.2), smooth),
           (W_('faint', 'billionth') - 0.2, W_('faint', 'Giant') - 0.1, (540, 700, 1.25), (540, 720, 1.35), smooth),
           (W_('faint', 'Giant') - 0.1, c_ctrl - 0.22, (560, 1000, 1.2), (540, 1060, 0.9), ease),
           whip_shot(c_ctrl - 0.22, c_ctrl, (540, 1060, 0.9), 1400)], exit='whip'),
    Scene('control', c_ctrl, c_drift, with_captions(s_control),
          [(c_ctrl, c_ctrl + 2.6, (540, 880, 1.0), (540, 860, 1.1), smooth),
           (c_ctrl + 2.6, T['skit'][0] - 0.05, (560, 760, 1.12), (570, 760, 1.2), smooth),
           (T['skit'][0] - 0.05, T['skit'][1] + 0.05, (260, 1000, 1.7), (260, 990, 1.8), smooth),
           (T['skit'][1] + 0.05, c_drift, (600, 640, 1.05), (600, 640, 1.12), smooth)]),
    Scene('drift', c_drift, c_bye, with_captions(s_drift, 0.9),
          [(c_drift, c_bye, (500, 900, 1.0), (480, 880, 1.06), smooth)]),
    Scene('goodbye', c_bye, END, with_captions(s_goodbye),
          [(c_bye, c_bye + 1.85, (620, 1150, 1.15), (630, 1140, 1.22), smooth),
           (c_bye + 1.85, END, (540, 1380, 1.18), (540, 1390, 1.23), smooth)]),
]

E.OVERLAY = captions
E.SHAKES[:] = [(W_('hook', 'tomorrow'), 24), (W_('date', 'first'), 18), (W_('date', 'light-day'), 7),
               (W_('miles', 'sixteen'), 8), (W_('loop', 'power'), 14), (W_('memory', 'memory'), 6),
               (W_('radio', 'weaker'), 7), (W_('faint', 'billionth'), 7), (W_('power', 'four'), 8),
               (OFFS['lecp'], 10), (W_('two', 'two'), 8)]

def sfx_events():
    ev = [(0.05, 'whoosh', 0.6)]
    for s in scenes[1:]: ev.append((s.start - 0.08, 'whoosh', 0.7))
    ev += [(W_('hook', 'message'), 'pop', 1.0), (W_('hook', 'tomorrow'), 'thud', 1.0),
           (W_('date', 'eighteenth'), 'pop', 0.9), (W_('date', 'first'), 'thud', 0.9),
           (W_('date', 'light-day'), 'pop', 0.9), (W_('miles', 'sixteen'), 'ding', 1.0),
           (W_('loop', 'power'), 'thud', 1.0), (c_bat + 0.1, 'ding', 0.5),
           (W_('memory', 'nineteen'), 'pop', 0.9), (W_('memory', 'memory'), 'pop', 0.8), (W_('memory', 'photo'), 'ding', 0.8),
           (W_('radio', 'weaker'), 'pop', 0.9), (W_('radio', 'bulb'), 'pop', 0.7),
           (W_('faint', 'billionth'), 'ding', 0.9), (W_('faint', 'Giant'), 'pop', 0.8),
           (W_('power', 'four'), 'pop', 0.9), (W_('two', 'two'), 'ding', 1.0), (W_('end', 'remember') + 0.05, 'pop', 0.9)]
    ev += [(v, 'tick', 2.5) for v in OFFS.values()]
    ev.append((OFFS['lecp'], 'thud', 0.6))
    for k in range(6): ev.append((W_('hook', 'today') + k * 0.2, 'tick', 1.2))
    return ev

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'stills':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        stills(scenes, END, [float(x) for x in sys.argv[3:]], out + '/s_{:06.2f}.png')
    elif mode == 'render':
        render(scenes, END, sys.argv[2], float(sys.argv[3]), min(END, float(sys.argv[4])))
    elif mode == 'bed':
        build_bed(END, sfx_events(), sys.argv[2], mood='mystery', seed=18112026, bpm=76)
    elif mode == 'end':
        print(END)
