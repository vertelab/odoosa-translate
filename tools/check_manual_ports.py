#!/usr/bin/env python3
"""check_manual_ports.py — kan manual/odoo-18.0/ kopieras till 19.0 och 20.0?

KRAV (manual/README.md): en post får bara ligga i manual/ om Odoo SA lämnat
den TOM i officiell sv.po. Om SA redan översatt den tar vi över deras text
och tappar deras framtida rättelser.

Detta skript jämför varje msgid i manual/odoo-18.0/<modul>.po mot
official-now.po i målutgåvan och rapporterar:
  TOM      → SA har posten men msgstr är tom/tomt utrymme  → säker att fylla
  SA-HAR   → SA har redan en översättning                  → FÅR EJ kopieras
  SAKNAD   → msgid finns inte i utgåvan                    → hoppa över
"""
import pathlib
import sys

import polib

ROOT = pathlib.Path("/srv/odoosa-translate")
SRC = ROOT / "manual" / "odoo-18.0"
TARGETS = ["19.0", "20.0"]

total_ok = total_bad = total_missing = 0

for target in TARGETS:
    print(f"\n=== {target} ===")
    for src in sorted(SRC.glob("*.po")):
        module = src.stem
        now = ROOT / "cache" / f"odoo-{target}" / module / "official-now.po"
        if not now.exists():
            print(f"  {module:<22} ⚠️  ingen official-now (kör fetch {target})")
            continue
        now_po = polib.pofile(str(now))
        idx = {e.msgid: e for e in now_po}
        src_po = polib.pofile(str(src))
        empty, sa_has, missing = [], [], []
        for e in src_po:
            tgt = idx.get(e.msgid)
            if tgt is None:
                # msgid kan ha ändrats mellan utgåvor — kolla om MODULEN alls finns
                missing.append(e.msgid[:60])
            elif tgt.msgstr.strip():
                sa_has.append((e.msgid[:50], len(tgt.msgstr)))
            else:
                empty.append(e.msgid[:50])
        mark = "✅" if not sa_has and empty else ("⚠️" if sa_has else "·")
        print(f"  {module:<22} {mark} tom={len(empty)} SA-har={len(sa_has)} saknad={len(missing)}")
        for msgid, ln in sa_has:
            print(f"       ⚠️  SA HAR REDAN ({ln} tecken): {msgid!r}")
        for msgid in missing:
            print(f"       ·   msgid borta i {target}: {msgid!r}")
        total_ok += len(empty)
        total_bad += len(sa_has)
        total_missing += len(missing)

print(f"\nSAMMANFATTNING: {total_ok} tomma luckor att fylla, "
      f"{total_bad} kollisioner (SA har redan), {total_missing} msgid borta")
sys.exit(1 if total_bad else 0)
