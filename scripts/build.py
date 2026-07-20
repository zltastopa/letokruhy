#!/usr/bin/env python3
"""Parse cached NRSR MP pages -> per-MP records -> per-term age distribution.

Outputs (under data/):
  - mps.csv        one row per (term, mp_id): name, party, birth_date, age_at_election
  - distribution.json  per-term ages + summary stats + election metadata

Age convention: age (in whole years) at the term's election date. Replacement
MPs (who joined mid-term) are included and normalized to the same election date,
so every term is a consistent snapshot of "the people who sat in this parliament".
"""
from __future__ import annotations

import csv
import html as htmllib
import json
import re
import statistics
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MP_DIR = ROOT / "cache" / "mp"
ROSTER_DIR = ROOT / "cache" / "rosters"
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)

# Slovak National Council election dates (reference date for "age at election").
# Term 1 was the 1994 snap election; terms run ~4 years (some shortened).
ELECTION = {
    1: date(1994, 10, 1),
    2: date(1998, 9, 26),
    3: date(2002, 9, 21),
    4: date(2006, 6, 17),
    5: date(2010, 6, 12),
    6: date(2012, 3, 10),
    7: date(2016, 3, 5),
    8: date(2020, 2, 29),
    9: date(2023, 9, 30),
}
TERM_LABEL = {
    1: "1994", 2: "1998", 3: "2002", 4: "2006", 5: "2010",
    6: "2012", 7: "2016", 8: "2020", 9: "2023",
}

MP_LINK = re.compile(r"PoslanecID=(\d+)&(?:amp;)?CisObdobia=(\d+)")
FIELD = re.compile(
    r"<strong>([^<]+)</strong>\s*<span>(.*?)</span>",
    re.DOTALL,
)
DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


# Corrections for the 3 MPs whose NRSR birth field is wrong/empty (data-entry
# errors on nrsr.sk). Verified against public sources; keyed by PoslanecID.
BIRTH_OVERRIDE = {
    765: (date(1968, 11, 16), "László Sólymos; NRSR shows 2010, corrected per Wikipedia/Wikidata"),
    795: (date(1971, 8, 31), "Erika Jurinová; NRSR shows 2010, corrected per Wikipedia"),
    998: (date(1977, 9, 9), "Martin Borguľa; NRSR empty, corrected per TASR/teraz.sk profile 2020"),
}


def parse_mp(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8")
    fields = {}
    for label, value in FIELD.findall(txt):
        fields[clean(label)] = clean(value)
    return fields


def parse_date(s: str):
    m = DATE_RE.search(s or "")
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def age_on(born: date, ref: date) -> int:
    return ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))


def rosters() -> dict[int, list[int]]:
    """Per-term MP ids. Base = NRSR alphabetical roster. For terms where the
    current roster page lists only sitting members (term 9), union in ids of
    everyone who cast a vote (data/extra_ids.json, derived from vote records),
    so every term consistently covers all who held the mandate."""
    extra_path = ROOT / "data" / "extra_ids.json"
    extra = {}
    if extra_path.exists():
        extra = {int(k): set(v) for k, v in json.loads(extra_path.read_text()).items()}
    out = {}
    for p in sorted(ROSTER_DIR.glob("term-*.html")):
        term = int(p.stem.split("-")[1])
        html = p.read_text(encoding="utf-8")
        ids = {int(a) for a, b in MP_LINK.findall(html) if int(b) == term}
        ids |= extra.get(term, set())
        out[term] = sorted(ids)
    return out


def main() -> None:
    rows = []
    missing_birth = []
    for term, ids in sorted(rosters().items()):
        ref = ELECTION[term]
        for mid in ids:
            page = MP_DIR / f"{mid}-{term}.html"
            if not page.exists():
                continue
            f = parse_mp(page)
            born = parse_date(f.get("Narodený(á)", ""))
            if mid in BIRTH_OVERRIDE:
                born = BIRTH_OVERRIDE[mid][0]
            name = " ".join(x for x in [f.get("Meno", ""), f.get("Priezvisko", "")] if x).strip()
            rec = {
                "term": term,
                "term_label": TERM_LABEL[term],
                "mp_id": mid,
                "name": name or f.get("Priezvisko", ""),
                "title": f.get("Titul", ""),
                "party": f.get("Kandidoval(a) za", ""),
                "nationality": f.get("Národnosť", ""),
                "birth_date": born.isoformat() if born else "",
                "age_at_election": age_on(born, ref) if born else "",
            }
            rows.append(rec)
            if not born:
                missing_birth.append((term, mid, name))

    # per-MP CSV
    with (OUT / "mps.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # per-term distribution + stats
    dist = []
    for term in sorted(ELECTION):
        ages = [r["age_at_election"] for r in rows
                if r["term"] == term and isinstance(r["age_at_election"], int)]
        if not ages:
            continue
        ages_sorted = sorted(ages)
        n = len(ages)
        q = statistics.quantiles(ages, n=4) if n >= 4 else [min(ages), statistics.median(ages), max(ages)]
        dist.append({
            "term": term,
            "label": TERM_LABEL[term],
            "election_date": ELECTION[term].isoformat(),
            "n": n,
            "n_seats": 150,
            "mean": round(statistics.mean(ages), 1),
            "median": statistics.median(ages),
            "min": min(ages),
            "max": max(ages),
            "q1": round(q[0], 1),
            "q3": round(q[2], 1),
            "stdev": round(statistics.pstdev(ages), 1),
            "ages": ages_sorted,
        })

    (OUT / "distribution.json").write_text(
        json.dumps({"terms": dist, "generated": date.today().isoformat()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total = len(rows)
    with_birth = sum(1 for r in rows if r["birth_date"])
    print(f"rows: {total}, with birth date: {with_birth}, missing: {len(missing_birth)}")
    for term in sorted(ELECTION):
        d = next((x for x in dist if x["term"] == term), None)
        if d:
            print(f"  {d['label']} (term {term}): n={d['n']:3d}  "
                  f"mean={d['mean']:.1f}  median={d['median']}  "
                  f"min={d['min']}  max={d['max']}")
    if missing_birth:
        print("missing birth dates (first 20):", missing_birth[:20])


if __name__ == "__main__":
    main()
