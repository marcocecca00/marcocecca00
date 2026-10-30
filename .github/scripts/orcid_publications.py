"""Refresh the publications block in README.md from the public ORCID API.

Usage: python orcid_publications.py <orcid-id> [readme-path] [max-items]
"""
import json
import re
import sys
import urllib.parse
import urllib.request

START, END = "<!-- ORCID:START -->", "<!-- ORCID:END -->"
TYPE_ICONS = {
    "journal-article": "📄",
    "conference-paper": "🎤",
    "conference-poster": "🪧",
    "preprint": "📝",
    "dissertation-thesis": "🎓",
    "book-chapter": "📘",
    "software": "💾",
    "data-set": "🗃️",
}


def fetch_works(orcid):
    req = urllib.request.Request(
        f"https://pub.orcid.org/v3.0/{orcid}/works",
        headers={"Accept": "application/json", "User-Agent": "profile-readme"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

    works = []
    for group in data.get("group", []):
        w = group["work-summary"][0]  # ORCID's preferred version of the work
        date = w.get("publication-date") or {}
        part = lambda k: int((date.get(k) or {}).get("value") or 0)
        doi = next(
            (
                e["external-id-value"]
                for e in (w.get("external-ids") or {}).get("external-id", [])
                if e["external-id-type"] == "doi" and e.get("external-id-relationship") == "self"
            ),
            None,
        )
        works.append({
            "title": w["title"]["title"]["value"].strip(),
            "venue": ((w.get("journal-title") or {}).get("value") or "").strip(),
            "year": part("year"),
            "sort": (part("year"), part("month"), part("day")),
            "type": w.get("type", ""),
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else (w.get("url") or {}).get("value"),
        })
    return sorted(works, key=lambda w: w["sort"], reverse=True)


def shields_escape(text):
    return urllib.parse.quote(text.replace("-", "--").replace("_", "__"), safe="")


def render(works, orcid, limit):
    lines = []
    for w in works[:limit]:
        icon = TYPE_ICONS.get(w["type"], "📄")
        title = f"[{w['title']}]({w['url']})" if w["url"] else w["title"]
        meta = " · ".join(str(x) for x in (f"*{w['venue']}*" if w["venue"] else "", w["year"] or "") if x)
        badge = (
            f" &nbsp;[![DOI](https://img.shields.io/badge/DOI-{shields_escape(w['doi'])}-24c6dc?style=flat-square)]({w['url']})"
            if w["doi"] else ""
        )
        lines.append(f"{icon} &nbsp;**{title}**<br/>\n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{meta}{badge}\n")
    if not lines:
        lines.append("_Coming soon._\n")
    lines.append(f"<sub>All works on [ORCID](https://orcid.org/{orcid}) →</sub>")
    return "\n".join(lines)


def main():
    orcid = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else "README.md"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    readme = open(path, encoding="utf-8").read()
    block = f"{START}\n{render(fetch_works(orcid), orcid, limit)}\n{END}"
    updated, n = re.subn(re.escape(START) + r".*?" + re.escape(END), lambda _: block, readme, flags=re.S)
    if n != 1:
        sys.exit(f"expected exactly one {START} ... {END} block in {path}, found {n}")
    if updated != readme:
        open(path, "w", encoding="utf-8").write(updated)
        print("README updated")
    else:
        print("no changes")


if __name__ == "__main__":
    main()
