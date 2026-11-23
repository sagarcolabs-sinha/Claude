"""Trim each voice line, lay them on one timeline, and write narration.wav + timeline.json
(line spans and per-word times, split by character proportion between pauses)."""
import sys, json, re, numpy as np, soundfile as sf
vo_dir, lines_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
SR = 24000
GAP = {'hook': 0.12, 'date': 0.05, 'miles': 0.10, 'loop': 0.18, 'memory': 0.15, 'radio': 0.08,
       'faint': 0.15, 'power': 0.05, 'skit': 0.10, 'two': 0.25, 'end': 0.0}
LEAD = 0.15
lines = json.load(open(lines_path))
chunks, tl, t = [np.zeros(int(LEAD * SR))], [], LEAD
for L in lines:
    a, sr = sf.read(f"{vo_dir}/{L['id']}.wav"); assert sr == SR
    idx = np.where(np.abs(a) > 0.01)[0]
    a = a[max(0, idx[0] - int(0.02 * SR)): idx[-1] + int(0.06 * SR)]
    dur = len(a) / SR
    # pauses inside the line (>=0.12 s of quiet) so word timing snaps to phrases
    env = np.convolve(np.abs(a), np.ones(240) / 240, 'same') > 0.008
    pauses, run = [], 0
    for i, v in enumerate(env):
        if not v: run += 1
        else:
            if run >= int(0.12 * SR): pauses.append(((i - run) / SR, i / SR))
            run = 0
    words = L['text'].split()
    phrases, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r'[,.:?!]$', w): phrases.append(cur); cur = []
    if cur: phrases.append(cur)
    # map phrases to speech segments
    segs, s0 = [], 0.0
    for p0, p1 in pauses: segs.append((s0, p0)); s0 = p1
    segs.append((s0, dur))
    if len(segs) != len(phrases):        # fall back: one segment for the whole line
        segs, phrases = [(0.0, dur)], [words]
    wt = []
    for (a0, a1), ph in zip(segs, phrases):
        n = sum(len(w) + 1 for w in ph); x = a0
        for w in ph:
            d = (a1 - a0) * (len(w) + 1) / n; wt.append([w, round(t + x, 3), round(t + x + d, 3)]); x += d
    tl.append({'id': L['id'], 'voice': L['voice'], 'text': L['text'], 'start': round(t, 3), 'end': round(t + dur, 3), 'words': wt,
               'segments_matched': len(segs) == len(phrases)})
    chunks.append(a); t += dur
    g = GAP[L['id']]; chunks.append(np.zeros(int(g * SR))); t += g
mix = np.concatenate(chunks)
sf.write(f"{out_dir}/narration.wav", mix, SR)
json.dump({'duration': round(len(mix) / SR, 3), 'lines': tl}, open(f"{out_dir}/timeline.json", 'w'), indent=1)
for L in tl: print(f"{L['start']:6.2f} {L['end']:6.2f} {L['id']:7s} matched={L['segments_matched']}")
print('total', len(mix) / SR)
