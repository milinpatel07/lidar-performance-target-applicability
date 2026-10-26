"""Generate fig_outcomes.tex (v25): outcome grid (frame division) and retention at 10^-2.
Counts: v24 fig_outcomes.tex (frame division, KITTI rule). Retention: A1_retention_applicable_cells.csv."""
import math, sys
import pandas as pd

a1 = pd.read_csv(sys.argv[1])
out = sys.argv[2]

# (label, setting in A1, established, applied, counts us[1e-2,.05,.1], counts ue[...])
rows = [
 ('KITTI distance', None),
 ('near $\\to$ far', ('KITTI distance','near','far', ['1/3/1','0/0/5','0/0/5'], ['5/0/0','0/3/2','0/0/5'])),
 ('far $\\to$ near', ('KITTI distance','far','near', ['4/1/0','5/0/0','5/0/0'], ['0/5/0','5/0/0','5/0/0'])),
 ('nuScenes distance', None),
 ('near $\\to$ far', ('nuScenes distance','near','far', ['5/0/0','4/1/0','0/0/5'], ['5/0/0','5/0/0','0/0/5'])),
 ('far $\\to$ near', ('nuScenes distance','far','near', ['0/5/0','2/3/0','5/0/0'], ['0/2/3','0/5/0','5/0/0'])),
 ('nuScenes weather', None),
 ('clear $\\to$ rain', ('nuScenes rain','clear','rain', ['0/2/0','0/5/0','0/4/1'], ['0/5/0','0/4/1','0/1/4'])),
 ('rain $\\to$ clear', ('nuScenes rain','rain','clear', ['0/0/0','5/0/0','5/0/0'], ['5/0/0','5/0/0','5/0/0'])),
 ('change of dataset and detector', None),
 ('nuScenes $\\to$ KITTI', ('change of dataset','nuScenes','KITTI', ['0/0/5','0/0/5','0/0/5'], ['5/0/0','5/0/0','5/0/0'])),
 ('KITTI $\\to$ nuScenes', ('change of dataset','KITTI','nuScenes', ['5/0/0','5/0/0','5/0/0'], ['0/5/0','0/5/0','0/5/0'])),
]

x = a1[(a1.alpha == 0.01) & (a1.variant == 'frame')]
def ret(setting, ind, est, app):
    g = x[(x.setting == setting) & (x.indicator == ind) & (x.established == est) & (x.applied == app)]
    return [100 * v for v in g.sort_values('seed').R_hat]

# geometry (cm)
XL = 2.62                       # right edge of row labels
cols = {('us',0): 2.75, ('ue',0): 3.90,               # pre-specified block
        ('us',1): 5.20, ('us',2): 6.35, ('ue',1): 7.70, ('ue',2): 8.85}
SQ, PITCH = 0.17, 0.205
R0, R1 = 10.10, 12.00            # retention axis x-range
def rx(p):                       # percent -> x on a log axis 0.01..100 %
    p = max(p, 0.01)
    return R0 + (math.log10(p) + 2) / 4 * (R1 - R0)

L = []
L.append(r'\input{preamble}')
L.append(r'\begin{document}')
L.append(r'\begin{tikzpicture}[font=\scriptsize]')
L.append(r'\tikzset{sq/.style={draw=edge, line width=0.25pt}}')
# layout of rows
y = 0.0
ys = []
for lab, spec in rows:
    if spec is None:
        y -= 0.42
        ys.append((lab, None, y))
    else:
        y -= 0.33
        ys.append((lab, spec, y))
ybot = y - 0.12
ytop = 0.10
# exploratory shading
L.append(r'\fill[expfill] (5.08,%.2f) rectangle (9.90,%.2f);' % (ybot, ytop + 0.95))
# headers
L.append(r'\node[font=\scriptsize\bfseries] at (3.83,%.2f) {target limit};' % (ytop + 0.75))
L.append(r'\node[font=\scriptsize\bfseries] at (7.49,%.2f) {exploratory limits\expl};' % (ytop + 0.75))
L.append(r'\node[font=\tiny] at (3.23,%.2f) {spatial $\us$};' % (ytop + 0.42))
L.append(r'\node[font=\tiny] at (4.38,%.2f) {existence $\ue$};' % (ytop + 0.42))
L.append(r'\node at (3.23,%.2f) {$10^{-2}$};' % (ytop + 0.12))
L.append(r'\node at (4.38,%.2f) {$10^{-2}$};' % (ytop + 0.12))
L.append(r'\node[font=\tiny] at (6.25,%.2f) {spatial $\us$};' % (ytop + 0.42))
L.append(r'\node[font=\tiny] at (8.80,%.2f) {existence $\ue$};' % (ytop + 0.42))
for (ind, k), x0 in cols.items():
    if k == 1: L.append(r'\node at (%.2f,%.2f) {0.05\expl};' % (x0 + 0.48, ytop + 0.12))
    if k == 2: L.append(r'\node at (%.2f,%.2f) {0.1\expl};' % (x0 + 0.48, ytop + 0.12))
L.append(r'\node[anchor=east, font=\tiny, text=ink!80, align=right] at (%.2f,%.2f) {threshold selected in\\ $\to$ used in};' % (XL, ytop + 0.30))
# retention axis header
L.append(r'\node[font=\scriptsize\bfseries, align=center] at (%.2f,%.2f) {retention at $10^{-2}$};' % ((R0 + R1) / 2, ytop + 0.75))
L.append(r'\node[font=\tiny, align=center] at (%.2f,%.2f) {applicable outcomes,\\ correct detections accepted};' % ((R0 + R1) / 2, ytop + 0.30))
# retention grid lines and ticks
for p, t in [(0.01, '0.01'), (0.1, '0.1'), (1, '1'), (10, '10'), (100, '100')]:
    xx = rx(p)
    L.append(r'\draw[ink!20, line width=0.3pt] (%.3f,%.2f) -- (%.3f,%.2f);' % (xx, ybot, xx, ytop))
    L.append(r'\node[font=\tiny, anchor=north] at (%.3f,%.2f) {%s};' % (xx, ybot - 0.02, t))
L.append(r'\node[font=\tiny, anchor=north] at (%.2f,%.2f) {\%%, log scale};' % ((R0 + R1) / 2, ybot - 0.26))
L.append(r'\draw[ink!60, line width=0.4pt] (%.2f,%.2f) -- (%.2f,%.2f);' % (R0, ybot, R1, ybot))

def squares(x0, y0, spec):
    a, n, d = (int(v) for v in spec.split('/'))
    out = []
    for k in range(5):
        if k < a: c = 'appc'
        elif k < a + n: c = 'ndc'
        elif k < a + n + d: c = 'nac'
        else: c = 'ntc'
        out.append(r'\filldraw[sq, fill=%s] (%.3f,%.3f) rectangle ++(%.2f,%.2f);' % (c, x0 + k * PITCH, y0, SQ, SQ))
    return out

for lab, spec, yy in ys:
    if spec is None:
        L.append(r'\node[anchor=west, font=\scriptsize\bfseries] at (0,%.2f) {%s};' % (yy + 0.06, lab))
        continue
    setting, est, app, cus, cue = spec
    L.append(r'\node[anchor=east] at (%.2f,%.3f) {%s};' % (XL, yy + 0.085, lab))
    for k in range(3):
        L += squares(cols[('us', k)], yy, cus[k])
        L += squares(cols[('ue', k)], yy, cue[k])
    # retention markers: u_s circles (upper lane), u_e triangles (lower lane)
    for ind, ylane, shape in [('u_s', yy + 0.15, 'circle'), ('u_e', yy + 0.02, 'tri')]:
        vals = ret(setting, ind, est, app)
        if not vals:
            continue
        own = ret(setting, ind, app, app)
        low = any(v < 0.01 for v in vals)
        for v in vals:
            xv = rx(v)
            if shape == 'circle':
                L.append(r'\fill[ink] (%.3f,%.3f) circle (0.05);' % (xv, ylane))
            else:
                L.append(r'\fill[ink] (%.3f,%.3f) -- ++(0.055,0.085) -- ++(0.055,-0.085) -- cycle;' % (xv - 0.055, ylane - 0.035))
        if own:   # open marker drawn last and larger, so it stays visible where it overlaps filled markers
            med = sorted(own)[len(own) // 2] if len(own) % 2 else sum(sorted(own)[len(own)//2-1:len(own)//2+1]) / 2
            xo = rx(med)
            if shape == 'circle':
                L.append(r'\draw[ink!60, line width=0.45pt] (%.3f,%.3f) circle (0.08);' % (xo, ylane))
            else:
                L.append(r'\draw[ink!60, line width=0.45pt] (%.3f,%.3f) -- ++(0.085,0.13) -- ++(0.085,-0.13) -- cycle;' % (xo - 0.085, ylane - 0.055))
        if low:
            L.append(r'\node[font=\tiny, anchor=east, inner sep=0.5pt] at (%.3f,%.3f) {$<$};' % (R0 - 0.01, ylane))
# legend
yl = ybot - 0.85
leg = [('appc', 'applicable'), ('ndc', 'not determined'), ('nac', 'not applicable'), ('ntc', 'no threshold selected')]
xpos = [0.0, 1.55, 3.45, 5.30]
for (c, t), xx in zip(leg, xpos):
    L.append(r'\filldraw[sq, fill=%s] (%.2f,%.2f) rectangle ++(%.2f,%.2f);' % (c, xx, yl, SQ, SQ))
    L.append(r'\node[anchor=west] at (%.2f,%.3f) {%s};' % (xx + 0.20, yl + 0.085, t))
L.append(r'\node[anchor=west, font=\tiny, text=ink!80] at (7.75,%.3f) {five squares per cell: one per split, sorted by outcome};' % (yl + 0.085))
y2 = yl - 0.40
L.append(r'\node[anchor=west] at (0,%.3f) {retention:};' % (y2 + 0.03))
L.append(r'\fill[ink] (1.40,%.3f) circle (0.05); \node[anchor=west] at (1.48,%.3f) {$\us$};' % (y2 + 0.03, y2 + 0.03))
L.append(r'\fill[ink] (2.00,%.3f) -- ++(0.055,0.085) -- ++(0.055,-0.085) -- cycle; \node[anchor=west] at (2.14,%.3f) {$\ue$}; \node[anchor=west, font=\tiny] at (2.55,%.3f) {transferred threshold, one marker per applicable split};' % (y2 - 0.01, y2 + 0.03, y2 + 0.03))
L.append(r'\draw[ink!60, line width=0.45pt] (7.35,%.3f) circle (0.08); \draw[ink!60, line width=0.45pt] (7.50,%.3f) -- ++(0.085,0.13) -- ++(0.085,-0.13) -- cycle; \node[anchor=west, font=\tiny] at (7.72,%.3f) {threshold selected in the condition of use (median)};' % (y2 + 0.03, y2 - 0.03, y2 + 0.03))
L.append(r'\end{tikzpicture}')
L.append(r'\end{document}')
open(out, 'w').write('\n'.join(L) + '\n')
