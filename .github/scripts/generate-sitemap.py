#!/usr/bin/env python3
"""
Generate sitemap.xml for davidmeldofsky.com.

Rules:
  - Scans the repo root (and any subfolders) for *.html files.
  - index.html            -> https://davidmeldofsky.com/
  - sub/index.html        -> https://davidmeldofsky.com/sub/
  - any other foo.html    -> https://davidmeldofsky.com/foo   (extensionless)
  - Pages with <meta name="robots" content="noindex"> are skipped automatically.
  - Pages listed in EXCLUDE are skipped.
  - <lastmod> is the file's last git commit date (YYYY-MM-DD), falling back to today.
    Commits marked SKIP_TOKEN are ignored, so bulk sweeps don't flatten every date.
  - Output is sorted homepage-first, then alphabetically.
"""

import datetime
import glob
import html
import os
import re
import subprocess

DOMAIN = "https://davidmeldofsky.com"

# Commits whose message contains this token are ignored when computing
# <lastmod>, so site-wide mechanical sweeps don't flatten every date to the
# same day. Usage: git commit -m "Add GA4 snippet [skip lastmod] [skip ci]"
SKIP_TOKEN = "[skip lastmod]"

# Repo-relative paths to leave out of the sitemap, even if indexable.
EXCLUDE = {
    # "draft-page.html",
}

NOINDEX_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
ROBOTS_ATTR = re.compile(r'name\s*=\s*["\']robots["\']', re.IGNORECASE)
NOINDEX_WORD = re.compile(r"\bnoindex\b", re.IGNORECASE)


def is_noindex(path):
    """Return True if the page carries a robots noindex directive."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            head = fh.read(8000)
    except OSError:
        return False
    for tag in NOINDEX_META.findall(head):
        if ROBOTS_ATTR.search(tag) and NOINDEX_WORD.search(tag):
            return True
    return False


def git_lastmod(path):
    """Last commit date for a file as YYYY-MM-DD, or today if unavailable.

    Commits whose message contains SKIP_TOKEN are ignored, so a mechanical
    site-wide sweep doesn't reset every <lastmod> to the same day. Falls back
    to the unfiltered date for files whose only commits are marked.
    """
    try:
        for extra in (["-F", f"--grep={SKIP_TOKEN}", "--invert-grep"], []):
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cs", *extra, "--", path],
                capture_output=True,
                text=True,
                check=True,
            )
            date = result.stdout.strip()
            if date:
                return date
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return datetime.date.today().isoformat()


def url_for(rel):
    """Map a repo-relative HTML path to its canonical extensionless URL."""
    if rel == "index.html":
        return DOMAIN + "/"
    if rel.endswith("/index.html"):
        return DOMAIN + "/" + rel[: -len("index.html")]
    return DOMAIN + "/" + rel[: -len(".html")]


def main():
    entries = []
    for found in glob.glob("**/*.html", recursive=True):
        rel = found.replace(os.sep, "/")
        if rel in EXCLUDE or is_noindex(rel):
            continue
        entries.append((url_for(rel), git_lastmod(rel)))

    # Homepage first, then alphabetical by URL.
    entries.sort(key=lambda e: (e[0] != DOMAIN + "/", e[0]))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "",
    ]
    for loc, lastmod in entries:
        lines += [
            "  <url>",
            f"    <loc>{html.escape(loc)}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            "  </url>",
            "",
        ]
    lines.append("</urlset>")
    output = "\n".join(lines) + "\n"

    with open("sitemap.xml", "w", encoding="utf-8") as fh:
        fh.write(output)

    print(f"Wrote sitemap.xml with {len(entries)} URL(s).")
    for loc, lastmod in entries:
        print(f"  {loc}  ({lastmod})")


if __name__ == "__main__":
    main()
