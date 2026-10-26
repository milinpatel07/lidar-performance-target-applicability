"""Diagrams of the applicability test for README.md and the site (schematics, no data).

Run from the repository root:  python site/images/make_diagrams.py site/images
Writes how_the_test_works.svg (three steps), how_the_test_works_animated.svg (the same with wrong detections moving
below the threshold in step 2; still when the viewer asks for reduced motion), where_the_test_fits.svg,
independent_units.svg and more_data_shorter_bar.svg. Mark positions come from a seeded random generator (seed 7);
they illustrate and are not data. Colours: the Okabe-Ito palette of site/interactive/style.css.
"""
import random
import sys
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
CORRECT, WRONG, APPL, NOTAPPL, NOTDET = "#0072b2", "#d55e00", "#009e73", "#d55e00", "#e6c700"
THRESH, INK, GREY, LIGHT, LINE = "#6a3d9a", "#1a1a1a", "#5a5a5a", "#eef2f7", "#d0d0d0"
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"


class Svg:
    def __init__(self, w, h, title, desc):
        self.w, self.h = w, h
        self.parts = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' "
                      f"role='img' aria-labelledby='t d'><title id='t'>{title}</title><desc id='d'>{desc}</desc>",
                      f"<rect width='{w}' height='{h}' fill='white'/>"]

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, t, size=15, weight="normal", fill=INK, anchor="start"):
        self.add(f"<text x='{x}' y='{y}' {FONT} font-size='{size}' font-weight='{weight}' fill='{fill}' "
                 f"text-anchor='{anchor}'>{t}</text>")

    def dot(self, x, y, r=5, extra=""):
        self.add(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{r}' fill='{CORRECT}' {extra}/>")

    def cross(self, x, y, d=5, extra=""):
        self.add(f"<path d='M{x-d:.1f},{y-d:.1f} L{x+d:.1f},{y+d:.1f} M{x-d:.1f},{y+d:.1f} L{x+d:.1f},{y-d:.1f}' "
                 f"stroke='{WRONG}' stroke-width='2.6' stroke-linecap='round' fill='none' {extra}/>")

    def arrow_def(self):
        self.add(f"<defs><marker id='a' viewBox='0 0 10 10' refX='8' refY='5' markerWidth='7' markerHeight='7' "
                 f"orient='auto'><path d='M0,0 L10,5 L0,10 z' fill='{GREY}'/></marker></defs>")

    def arrow(self, x1, y1, x2, y2):
        self.add(f"<path d='M{x1},{y1} L{x2},{y2}' stroke='{GREY}' stroke-width='2.5' marker-end='url(#a)'/>")

    def write(self, name):
        (OUT / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8", newline="\n")
        print("wrote", OUT / name)


def three_steps(animated):
    rnd = random.Random(7)
    s = Svg(960, 400, "How the applicability test works",
            "Schematic in three steps, no data: a threshold on the uncertainty is chosen in one condition, kept "
            "unchanged in another condition where more wrong detections fall below it, and an interval of the share "
            "of wrong detections passed on is compared with the limit, giving applicable, not determined or not "
            "applicable.")
    s.arrow_def()
    if animated:
        s.add("<style>.drift{animation:drift 7s ease-in-out infinite}"
              "@keyframes drift{0%,15%{transform:translate(0,0)}45%,85%{transform:translate(var(--dx),0)}"
              "100%{transform:translate(0,0)}}"
              "@media (prefers-reduced-motion: reduce){.drift{animation:none;transform:translate(var(--dx),0)}}</style>")

    def panel(x0, step, title, sub, n_ok, wrong, tau, note):
        s.text(x0, 34, step, 13, "bold", GREY)
        s.text(x0, 58, title, 17, "bold")
        s.text(x0, 80, sub, 14, "normal", GREY)
        s.add(f"<rect x='{x0}' y='130' width='{tau - x0}' height='120' fill='{LIGHT}'/>")
        s.text(x0 + 6, 124, "passed on", 12, "normal", GREY)
        for _ in range(n_ok):
            s.dot(x0 + 12 + rnd.betavariate(2, 5) * 220, rnd.uniform(150, 235))
        for x, y, dx in wrong:
            if animated and dx:
                s.add(f"<g class='drift' style='--dx:{dx:.0f}px'>")
                s.cross(x, y)
                s.add("</g>")
            else:
                s.cross(x + dx, y)
        s.add(f"<line x1='{x0}' y1='256' x2='{x0 + 255}' y2='256' stroke='{INK}' stroke-width='1.5'/>")
        s.text(x0, 276, "low", 12, "normal", GREY)
        s.text(x0 + 255, 276, "high uncertainty", 12, "normal", GREY, "end")
        s.add(f"<line x1='{tau}' y1='104' x2='{tau}' y2='262' stroke='{THRESH}' stroke-width='2.4' "
              f"stroke-dasharray='6 4'/>")
        s.text(tau + 5, 116, "threshold", 12, "bold", THRESH)
        for i, line in enumerate(note):
            s.text(x0, 310 + 20 * i, line, 14)

    def wrong_marks(x0, n, n_moving, tau):
        out = []
        for i in range(n):
            x = x0 + 12 + rnd.betavariate(6, 1.6) * 220
            dx = (tau - 18 - rnd.uniform(0, 90)) - x if i < n_moving else 0
            out.append((x, rnd.uniform(150, 235), dx))
        return out

    panel(30, "STEP 1", "Choose a threshold", "condition of selection, e.g. clear weather", 26,
          wrong_marks(30, 7, 0, 170), 170, ["Few wrong detections pass:", "the target is met here."])
    s.arrow(300, 190, 330, 190)
    panel(345, "STEP 2", "Keep it unchanged", "condition of use, e.g. rain", 22,
          wrong_marks(345, 14, 6, 485), 485, ["More wrong detections pass:", "is the target still met?"])
    s.arrow(615, 190, 645, 190)
    x0 = 665
    s.text(x0, 34, "STEP 3", 13, "bold", GREY)
    s.text(x0, 58, "Decide with the data", 17, "bold")
    s.text(x0, 80, "share of passed detections that are wrong", 14, "normal", GREY)
    top, bottom, limit_y = 112, 262, 190
    s.add(f"<line x1='{x0 + 8}' y1='{top}' x2='{x0 + 8}' y2='{bottom}' stroke='{INK}' stroke-width='1.5'/>")
    s.text(x0 + 2, top - 4, "more", 12, "normal", GREY)
    s.text(x0 + 2, bottom + 14, "less", 12, "normal", GREY)
    s.add(f"<line x1='{x0 + 8}' y1='{limit_y}' x2='{x0 + 280}' y2='{limit_y}' stroke='{INK}' stroke-width='2' "
          f"stroke-dasharray='6 4'/>")
    s.text(x0 + 280, limit_y - 8, "limit of the target", 12, "bold", INK, "end")
    for cx, lo, hi, label, col in ((x0 + 55, 222, 252, "applicable", APPL), (x0 + 145, 160, 230, "not determined", NOTDET),
                                    (x0 + 235, 122, 168, "not applicable", NOTAPPL)):
        s.add(f"<line x1='{cx}' y1='{lo}' x2='{cx}' y2='{hi}' stroke='{col}' stroke-width='10' stroke-linecap='round'/>")
        if col == NOTDET:
            s.add(f"<line x1='{cx}' y1='{lo}' x2='{cx}' y2='{hi}' stroke='#7a6a00' stroke-width='1' "
                  f"stroke-linecap='round' fill='none'/>")
        words = label.split(" ", 1) if " " in label else [label]
        for k, word in enumerate(words):
            s.text(cx, bottom + 30 + 16 * k, word, 13, "bold", "#7a6a00" if col == NOTDET else col, "middle")
    s.text(x0, 340, "The bar is the range in which the share", 14)
    s.text(x0, 360, "lies; more independent data shorten it.", 14)
    lx, ly = 30, 384
    s.dot(lx + 5, ly - 4)
    s.text(lx + 16, ly, "correct detection", 13, "normal", GREY)
    s.cross(lx + 150, ly - 4)
    s.text(lx + 161, ly, "wrong detection", 13, "normal", GREY)
    s.text(345, ly, "Schematic, not data.", 13, "normal", GREY)
    s.write("how_the_test_works_animated.svg" if animated else "how_the_test_works.svg")


def where_it_fits():
    boxes = [("Vehicle", "acceptance criterion", "set for the whole vehicle"),
             ("Detector", "performance target", "limit on wrong outputs"),
             ("Condition of selection", "threshold chosen", "with a statistical guarantee"),
             ("Applicability test", "in each potential", "triggering condition"),
             ("Safety argument", "outcome and measure", "use, change or record more")]
    w, h, bw, gap = 960, 190, 164, 28
    s = Svg(w, h, "Where the applicability test fits in a SOTIF analysis",
            "Chain of five boxes: an acceptance criterion for the vehicle is allocated as a performance target to the "
            "detector; a threshold is chosen in the condition of selection; the applicability test checks it in each "
            "potential triggering condition; the outcome and the measure that follows enter the safety argument.")
    s.arrow_def()
    for i, (a, b, c) in enumerate(boxes):
        x = 20 + i * (bw + gap)
        mine = i == 3
        s.add(f"<rect x='{x}' y='40' width='{bw}' height='108' rx='10' fill='{'#e7f4ef' if mine else LIGHT}' "
              f"stroke='{APPL if mine else LINE}' stroke-width='{2.5 if mine else 1.2}'/>")
        s.text(x + bw / 2, 72, a, 14, "bold", APPL if mine else INK, "middle")
        s.text(x + bw / 2, 96, b, 14, "normal", INK, "middle")
        s.text(x + bw / 2, 124, c, 12 if not mine else 14, "normal", GREY if not mine else INK, "middle")
        if i < len(boxes) - 1:
            s.arrow(x + bw + 3, 94, x + bw + gap - 3, 94)
    s.text(20, 26, "Where the test fits in a safety analysis according to ISO 21448 (SOTIF)", 15, "bold")
    s.text(20, 178, "Schematic. The test needs no access to the detector, only a table of its outputs.", 12, "normal", GREY)
    s.write("where_the_test_fits.svg")


def independent_units():
    rnd = random.Random(3)
    s = Svg(960, 230, "Frames of one drive are not independent",
            "Three recorded drives, each with ten frames. Frames within a drive share road, weather and traffic and "
            "look alike, so the thirty frames count as three independent units.")
    s.text(20, 28, "Thirty frames, but only three independent units", 16, "bold")
    s.text(20, 50, "Frames of one drive share the road, the weather and the traffic: they repeat one another.", 13,
           "normal", GREY)
    shades = [("#cfe3f3", "drive 1"), ("#fde0c8", "drive 2"), ("#d6efe5", "drive 3")]
    for d, (col, name) in enumerate(shades):
        x0 = 20 + d * 315
        s.add(f"<rect x='{x0}' y='68' width='295' height='118' rx='10' fill='none' stroke='{GREY}' "
              f"stroke-width='1.5' stroke-dasharray='5 4'/>")
        s.text(x0 + 10, 88, name, 13, "bold", GREY)
        for f in range(10):
            fx, fy = x0 + 12 + (f % 5) * 56, 98 + (f // 5) * 40
            s.add(f"<rect x='{fx}' y='{fy}' width='48' height='32' rx='4' fill='{col}' stroke='{LINE}'/>")
            s.add(f"<path d='M{fx + 4},{fy + 26} Q{fx + 24},{fy + 10 + rnd.uniform(-2, 2):.1f} {fx + 44},{fy + 26}' "
                  f"stroke='{GREY}' stroke-width='1.2' fill='none'/>")
        s.text(x0 + 147, 206, "= 1 unit", 14, "bold", INK, "middle")
    s.text(20, 226, "Count recorded sequences (drives, scenes) as units when their frames depend on each other.", 12,
           "normal", GREY)
    s.write("independent_units.svg")


def more_data():
    s = Svg(960, 300, "More independent data make the decision possible",
            "Three intervals of the share of wrong passed-on detections around the same estimate, from few, more and "
            "many independent units. Only the shortest interval lies entirely below the limit: not determined, not "
            "determined, applicable.")
    s.text(20, 28, "More independent data shorten the bar until it can decide", 16, "bold")
    limit_y, base = 110, 228
    s.add(f"<line x1='20' y1='{limit_y}' x2='940' y2='{limit_y}' stroke='{INK}' stroke-width='2' stroke-dasharray='6 4'/>")
    s.text(940, limit_y - 8, "limit of the target", 12, "bold", INK, "end")
    est = 150
    for i, (n, half, lab, col) in enumerate((("few units", 70, "not determined", NOTDET),
                                              ("more units", 45, "not determined", NOTDET),
                                              ("many units", 22, "applicable", APPL))):
        cx = 170 + i * 300
        s.add(f"<line x1='{cx}' y1='{est - half}' x2='{cx}' y2='{est + half}' stroke='{col}' stroke-width='12' "
              f"stroke-linecap='round'/>")
        s.add(f"<circle cx='{cx}' cy='{est}' r='4' fill='{INK}'/>")
        s.text(cx, base + 26, n, 14, "bold", INK, "middle")
        s.text(cx, base + 44, lab, 13, "bold", "#7a6a00" if col == NOTDET else col, "middle")
    s.text(20, 292, "Schematic: the same estimate (dot), measured on few, more and many independent units. Here the estimate "
           "lies below the limit; it can equally lie above it.", 12, "normal", GREY)
    s.write("more_data_shorter_bar.svg")


if __name__ == "__main__":
    three_steps(False)
    three_steps(True)
    where_it_fits()
    independent_units()
    more_data()
