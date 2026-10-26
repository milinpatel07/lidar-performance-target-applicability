"""Link preview of the site (1280 x 640): the question and the three-step schematic of how_the_test_works.svg.

Run from the repository root:  python site/images/make_social_preview.py site/images/social_preview.svg
social_preview.png is this SVG rendered by a browser at 1280 x 640 pixels (link previews need a raster image).
"""
import sys
from pathlib import Path

out = Path(sys.argv[1])
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"
INK, GREY, BLUE = "#1f2328", "#59636e", "#1f5fbf"
s = f"""<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' viewBox='0 0 1280 640' width='1280' height='640'>
<rect width='1280' height='640' fill='white'/>
<rect width='1280' height='10' fill='{BLUE}'/>
<text x='60' y='92' {FONT} font-size='44' font-weight='bold' fill='{INK}'>Does the threshold still hold?</text>
<text x='60' y='140' {FONT} font-size='25' fill='{GREY}'>A statistical test of whether an uncertainty threshold that meets its performance target</text>
<text x='60' y='174' {FONT} font-size='25' fill='{GREY}'>in one condition still meets it under a triggering condition (ISO 21448, SOTIF).</text>
<image x='60' y='205' width='1160' height='420' href='how_the_test_works.svg' xlink:href='how_the_test_works.svg'/>
</svg>
"""
out.write_text(s, encoding="utf-8", newline="\n")
print("wrote", out)
