"""Schematic of the applicability test (no data), shown in README.md and on the start page of the site.

Run from the repository root:  python site/images/make_how_the_test_works.py site/images/how_the_test_works.svg
The positions of the marks come from a seeded random generator (seed 7); they illustrate, they are not data.
"""
import random
import sys

OUT = sys.argv[1]
W, H = 960, 400
BLUE, ORANGE, INK, GREY, LIGHT = "#1f5fbf", "#d95f02", "#1f2328", "#6e7781", "#eef2f7"
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"
rnd = random.Random(7)
s = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}' role='img' "
     f"aria-labelledby='t d'><title id='t'>How the applicability test works</title><desc id='d'>Schematic in three "
     f"steps, no data: a threshold on the uncertainty is chosen in one condition, kept unchanged in another condition "
     f"where more wrong detections fall below it, and an interval of the share of wrong detections passed on is compared "
     f"with the limit, giving applicable, not determined or not applicable.</desc>",
     f"<rect width='{W}' height='{H}' fill='white'/>"]


def text(x, y, t, size=15, weight="normal", fill=INK, anchor="start"):
    s.append(f"<text x='{x}' y='{y}' {FONT} font-size='{size}' font-weight='{weight}' fill='{fill}' "
             f"text-anchor='{anchor}'>{t}</text>")


def dot(x, y):
    s.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='5' fill='{BLUE}'/>")


def cross(x, y):
    d = 5
    s.append(f"<path d='M{x-d:.1f},{y-d:.1f} L{x+d:.1f},{y+d:.1f} M{x-d:.1f},{y+d:.1f} L{x+d:.1f},{y-d:.1f}' "
             f"stroke='{ORANGE}' stroke-width='2.6' stroke-linecap='round'/>")


def detections(x0, n_ok, n_wrong, wrong_low, row_y=(150, 235)):
    """Detections on an uncertainty axis from x0 to x0 + 250; correct ones low, wrong ones high."""
    for _ in range(n_ok):
        dot(x0 + 12 + rnd.betavariate(2, 5) * 220, rnd.uniform(*row_y))
    for i in range(n_wrong):
        a, b = (6, 1.6) if i >= wrong_low else (1.6, 3.5)
        cross(x0 + 12 + rnd.betavariate(a, b) * 220, rnd.uniform(*row_y))


def panel(x0, step, title, sub, n_ok, n_wrong, wrong_low, tau, note):
    text(x0, 34, step, 13, "bold", GREY)
    text(x0, 58, title, 17, "bold")
    text(x0, 80, sub, 14, "normal", GREY)
    s.append(f"<rect x='{x0}' y='130' width='{tau - x0}' height='120' fill='{LIGHT}'/>")
    text(x0 + 6, 124, "passed on", 12, "normal", GREY)
    detections(x0, n_ok, n_wrong, wrong_low)
    s.append(f"<line x1='{x0}' y1='256' x2='{x0 + 255}' y2='256' stroke='{INK}' stroke-width='1.5'/>")
    text(x0, 276, "low", 12, "normal", GREY)
    text(x0 + 255, 276, "high uncertainty", 12, "normal", GREY, "end")
    s.append(f"<line x1='{tau}' y1='104' x2='{tau}' y2='262' stroke='{INK}' stroke-width='2.2' stroke-dasharray='6 4'/>")
    text(tau + 5, 116, "threshold", 12, "bold")
    for i, line in enumerate(note):
        text(x0, 310 + 20 * i, line, 14)


panel(30, "STEP 1", "Choose a threshold", "condition of selection, e.g. near distance", 26, 7, 1, 170,
      ["Few wrong detections pass:", "the target is met here."])
s.append(f"<path d='M300,190 L330,190' stroke='{GREY}' stroke-width='2.5' marker-end='url(#a)'/>")
panel(345, "STEP 2", "Keep it unchanged", "condition of use, e.g. rain", 22, 14, 5, 485,
      ["More wrong detections pass:", "is the target still met?"])
s.append(f"<path d='M615,190 L645,190' stroke='{GREY}' stroke-width='2.5' marker-end='url(#a)'/>")
s.insert(2, f"<defs><marker id='a' viewBox='0 0 10 10' refX='8' refY='5' markerWidth='7' markerHeight='7' "
            f"orient='auto'><path d='M0,0 L10,5 L0,10 z' fill='{GREY}'/></marker></defs>")

# step 3: interval of the share of wrong detections passed on against the limit
x0 = 665
text(x0, 34, "STEP 3", 13, "bold", GREY)
text(x0, 58, "Decide with the data", 17, "bold")
text(x0, 80, "share of passed detections that are wrong", 14, "normal", GREY)
top, bottom, limit_y = 112, 262, 190
s.append(f"<line x1='{x0 + 8}' y1='{top}' x2='{x0 + 8}' y2='{bottom}' stroke='{INK}' stroke-width='1.5'/>")
text(x0 + 2, top - 4, "more", 12, "normal", GREY)
text(x0 + 2, bottom + 14, "less", 12, "normal", GREY)
s.append(f"<line x1='{x0 + 8}' y1='{limit_y}' x2='{x0 + 280}' y2='{limit_y}' stroke='{ORANGE}' stroke-width='2' "
         f"stroke-dasharray='6 4'/>")
text(x0 + 280, limit_y - 8, "limit of the target", 12, "bold", ORANGE, "end")
for cx, lo, hi, label, col in ((x0 + 55, 222, 252, "applicable", BLUE), (x0 + 145, 160, 230, "not determined", GREY),
                                (x0 + 235, 122, 168, "not applicable", ORANGE)):
    s.append(f"<line x1='{cx}' y1='{lo}' x2='{cx}' y2='{hi}' stroke='{col}' stroke-width='9' stroke-linecap='round'/>")
    for k, word in enumerate(label.split(" ", 1) if " " in label else [label]):
        text(cx, bottom + 30 + 16 * k, word, 13, "bold", col, "middle")
text(x0, 340, "The bar is the range in which the share", 14)
text(x0, 360, "lies; more independent data shorten it.", 14)

# legend
lx, ly = 30, 384
dot(lx + 5, ly - 4)
text(lx + 16, ly, "correct detection", 13, "normal", GREY)
cross(lx + 150, ly - 4)
text(lx + 161, ly, "wrong detection", 13, "normal", GREY)
text(345, ly, "Schematic, not data.", 13, "normal", GREY)
s.append("</svg>")
open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(s) + "\n")
print("wrote", OUT)
