#!/usr/bin/env python3
"""Scrape Slovak parliament (NRSR) MP rosters and detail pages.

From first principles, using only public NRSR pages:
  1. Per-term alphabetical roster: sid=poslanci/zoznam_abc&CisObdobia=<term>
     -> gives every PoslanecID that served in that term (incl. replacements).
  2. Per-MP detail page: sid=poslanci/poslanec&PoslanecID=<id>&CisObdobia=<term>
     -> gives birth date ("Narodený(á)"), party ("Kandidoval(a) za"), name, etc.

Everything is cached as raw HTML so re-runs are cheap and offline-reproducible.
"""
from __future__ import annotations

import json
import re
import ssl
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache"
ROSTER_DIR = CACHE / "rosters"
MP_DIR = CACHE / "mp"
for d in (ROSTER_DIR, MP_DIR):
    d.mkdir(parents=True, exist_ok=True)

BASE = "https://www.nrsr.sk/web/Default.aspx"
UA = {"User-Agent": "Mozilla/5.0 (NRSR age-distribution research; polite scraper)"}
TERMS = list(range(1, 10))  # 1994 (term 1) .. 2023 (term 9)

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

MP_LINK = re.compile(r"PoslanecID=(\d+)&(?:amp;)?CisObdobia=(\d+)")


def fetch(url: str, retries: int = 4) -> str:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed {url}: {last}")


def roster_url(term: int) -> str:
    return f"{BASE}?sid=poslanci/zoznam_abc&CisObdobia={term}"


def mp_url(mp_id: int, term: int) -> str:
    return f"{BASE}?sid=poslanci/poslanec&PoslanecID={mp_id}&CisObdobia={term}"


def get_cached(path: Path, url: str) -> str:
    if path.exists() and path.stat().st_size > 0:
        return path.read_text(encoding="utf-8")
    html = fetch(url)
    path.write_text(html, encoding="utf-8")
    time.sleep(0.25)  # be polite on cache-miss
    return html


def scrape_rosters() -> dict[int, set[int]]:
    """term -> set of PoslanecID that served that term."""
    rosters: dict[int, set[int]] = {}
    for term in TERMS:
        html = get_cached(ROSTER_DIR / f"term-{term}.html", roster_url(term))
        ids = {int(a) for a, b in MP_LINK.findall(html) if int(b) == term}
        rosters[term] = ids
        print(f"roster term {term}: {len(ids)} MPs", flush=True)
    return rosters


def scrape_mp_pages(rosters: dict[int, set[int]]) -> None:
    pairs = sorted({(mid, t) for t, ids in rosters.items() for mid in ids})
    print(f"fetching {len(pairs)} MP detail pages (concurrency=6)...", flush=True)
    todo = [(m, t) for m, t in pairs if not (MP_DIR / f"{m}-{t}.html").exists()]
    print(f"  {len(pairs) - len(todo)} cached, {len(todo)} to fetch", flush=True)

    done = 0

    def work(pair):
        mid, t = pair
        get_cached(MP_DIR / f"{mid}-{t}.html", mp_url(mid, t))
        return pair

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(work, p) for p in todo]
        for f in as_completed(futs):
            f.result()
            done += 1
            if done % 100 == 0:
                print(f"  fetched {done}/{len(todo)}", flush=True)
    print("done fetching MP pages", flush=True)


def merge_extra_ids(rosters: dict[int, set[int]]) -> None:
    """Fold in MPs listed in data/extra_ids.json (e.g. term-9 members who left
    the current roster). Keeps the fetch set consistent with build.py."""
    path = ROOT / "data" / "extra_ids.json"
    if not path.exists():
        return
    extra = json.loads(path.read_text(encoding="utf-8"))
    for term_str, ids in extra.items():
        rosters.setdefault(int(term_str), set()).update(ids)


if __name__ == "__main__":
    rosters = scrape_rosters()
    merge_extra_ids(rosters)
    scrape_mp_pages(rosters)
    total = sum(len(v) for v in rosters.values())
    print(f"total (mp,term) pairs: {total}", file=sys.stderr)
