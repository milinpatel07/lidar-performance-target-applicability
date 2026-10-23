#!/usr/bin/env python3
"""check_links.py - links between the files of this repository resolve, without network access.

  - Markdown files: every relative link resolves to a file or folder of the repository.
  - HTML pages under site/: every relative href or src resolves inside site/, because GitHub Pages serves only site/;
    a link to a folder needs its index.html. Pages reach documentation and code by absolute GitHub URLs.
  - Every file: an absolute URL into this repository (github.com/<repo>/blob|tree/main/<path>) names an existing path,
    and a URL of its GitHub Pages site (<user>.github.io/<repo>/<path>) names an existing file under site/.

    python3 tests/check_links.py     # from the repository root; exit 1 on a broken link
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
REPO = r"https://github\.com/milinpatel07/lidar-performance-target-applicability/(?:blob|tree)/main/"
PAGES = r"https://milinpatel07\.github\.io/lidar-performance-target-applicability/"
TEXT = {".md", ".html", ".js", ".mjs", ".py", ".json", ".css", ".yml", ".cff", ".txt", ".tex", ".ipynb", ".toml"}
SKIP = {".git", "node_modules", "__pycache__"}


def relative_links(p, text):
    if p.suffix == ".md":
        found = re.findall(r"\]\(([^)\s]+)", text)
    elif p.suffix == ".html":
        found = re.findall(r"(?:href|src)\s*=\s*[\"']([^\"']+)[\"']", text)
    else:
        return []
    out = []
    for link in found:
        link = re.split(r"[?#]", link, maxsplit=1)[0]
        if link and not re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", link) and not link.startswith("//"):
            out.append(link)
    return out


def check(root=ROOT):
    site = (root / "site").resolve()
    bad = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if not p.is_file() or SKIP.intersection(rel.parts) or p.suffix not in TEXT:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        in_site = site in p.resolve().parents
        for link in relative_links(p, text):
            t = (p.parent / link).resolve()
            if not t.exists():
                bad.append(f"{rel.as_posix()}: {link} does not exist")
            elif p.suffix == ".html" and in_site and t != site and site not in t.parents:
                bad.append(f"{rel.as_posix()}: {link} lies outside site/ (GitHub Pages serves only site/)")
            elif p.suffix == ".html" and t.is_dir() and not (t / "index.html").exists():
                bad.append(f"{rel.as_posix()}: {link} is a folder without index.html")
        for m in re.finditer(REPO + r"([^\s\"'<>)`\]#?]+)", text):
            path = m.group(1).rstrip(".,;:")
            if "{" in path or "$" in path or "+" in path:   # URL built at run time in a script
                continue
            if not (root / path).exists():
                bad.append(f"{rel.as_posix()}: repository URL to missing path {path}")
        for m in re.finditer(PAGES + r"([^\s\"'<>)`\]#?]*)", text):
            path = m.group(1).rstrip(".,;:")
            if "{" in path or "$" in path or "+" in path:
                continue
            t = root / "site" / path
            if not (t.is_file() or (t / "index.html").is_file()):
                bad.append(f"{rel.as_posix()}: GitHub Pages URL to missing page {path or '(start page)'}")
    return bad


def main():
    bad = check()
    for b in bad:
        print(b)
    print(f"links checked: {len(bad)} broken")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
