#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
odoosa.py — Odoo SA Translation pipeline (Vertel style)
=======================================================
Kontinuerlig, multi-utgåva svensk översättning av Odoo-kärnan baserad på
Odoo SAs officiella översättningar och våra begrepp (glossary + regler).

Subkommandon:
  fetch [--versions 18.0,19.0] [--modules a,b]   Hämta officiella sv.po per utgåva → cache/
  apply  [--versions ...]      Applicera regler (core + per-version) på official-now
  merge  [--versions ...]      Trevägs-merge (last vs now vs desired) → klassificering
  build  [--versions ...]      Bygg i18n/sv.po + i18n_extra/sv.po + diff.po + report.md
  run    [--versions ...]      Hela pipelinen (fetch → apply → merge → build)
  publish [--message ...] [--dry-run]
                               Commit + push artefakter/regler/ordlista till GitHub
                               (körs av arbetsminionen; SSH deploy key)
  regression [--versions ...]  Jämför byggresultat mot gamla snapshot-po (task 1.4)
  check-edition <edition>      Verifiera i18n_extra-stöd (ny-utgåva-procedur, task 2.5)

Semantik:
  · Regler appliceras på msgstr (aldrig msgid), längsta match först.
  · only_if_msgid = regex som måste matcha msgid.
  · Trevägs-merge enligt beslutstabellen (8 användarfall) — se specs/odoosa-convergence.
  · Utländska l10n_*-moduler byggs/deployas aldrig (endast l10n_se).
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import polib
import requests
import yaml

DEFAULT_VERSIONS = ["18.0", "19.0"]
GITHUB_API = "https://api.github.com/repos/odoo/odoo"
RAW = "https://raw.githubusercontent.com/odoo/odoo"

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
BUILD_DIR = ROOT / "build"
RULES_DIR = ROOT / "rules"
REPORTS_DIR = ROOT / "reports"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "odoosa-translate/0.1"})


# ---------------------------------------------------------------------------
# Hjälpfunktioner
# ---------------------------------------------------------------------------

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def is_foreign_l10n(module):
    """Utländska l10n_*-moduler (l10n_de, l10n_fr, l10n_pl ...) — aldrig byggas.
    Endast l10n_se är relevant för Sverige."""
    return module.startswith("l10n_") and module != "l10n_se"


def edition_cache(edition):
    d = CACHE_DIR / f"odoo-{edition}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def module_cache(edition, module):
    d = edition_cache(edition) / module
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_json(url, retries=3, backoff=10):
    """GET med rate-limit-hantering (GitHub API)."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 429):
                wait = backoff * (attempt + 1)
                log(f"⏳ Rate limit (HTTP {r.status_code}) — väntar {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
        except requests.RequestException as e:
            if attempt == retries - 1:
                raise
            log(f"⚠️ {e} — retry {attempt + 1}/{retries}")
            time.sleep(backoff)
    raise RuntimeError(f"Kunde inte hämta {url}")


def github_tree(edition):
    """Alla filer i odoo/odoo <edition> (git tree, recursive)."""
    url = f"{GITHUB_API}/git/trees/{edition}?recursive=1"
    data = get_json(url)
    paths = [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]
    return paths


def parse_sv_po_path(path):
    """'addons/<mod>/i18n/sv.po' → mod; 'odoo/addons/base/i18n/sv.po' → base; annars None."""
    m = re.match(r"(?:odoo/)?addons/([^/]+)/i18n/sv\.po$", path)
    return m.group(1) if m else None


def fetch_raw(url, retries=3, backoff=5):
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=90)
            if r.status_code == 404:
                raise requests.HTTPError(f"404 Not Found: {url}")  # inga retries
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            if "404" in str(e) or attempt == retries - 1:
                raise
            log(f"⚠️ {e} — retry {attempt + 1}/{retries}")
            time.sleep(backoff)


# ---------------------------------------------------------------------------
# 1) FETCH
# ---------------------------------------------------------------------------

def fetch_official_po(edition, module):
    """Ladda ner officiell sv.po för modul i utgåva; base ligger på odoo/addons/base."""
    if module == "base":
        url = f"{RAW}/{edition}/odoo/addons/base/i18n/sv.po"
    else:
        url = f"{RAW}/{edition}/addons/{module}/i18n/sv.po"
    return fetch_raw(url)


def fetch_edition(edition, modules=None):
    """Rotera official-now → official-last, ladda ner nya official-now."""
    log(f"🌐 FETCH {edition}")
    tree_paths = github_tree(edition)
    all_mods = sorted({p for p in (parse_sv_po_path(x) for x in tree_paths) if p})
    wanted = [m for m in all_mods if not is_foreign_l10n(m)]
    if modules:
        wanted = [m for m in wanted if m in modules]
    log(f"   {len(wanted)} moduler med sv.po (av {len(all_mods)}; l10n_* exkluderade)")

    stats = {"ok": 0, "fail": 0, "missing": []}
    for mod in wanted:
        mdir = module_cache(edition, mod)
        now_path = mdir / "official-now.po"
        last_path = mdir / "official-last.po"
        if now_path.exists():
            if last_path.exists():
                last_path.unlink()
            now_path.rename(last_path)
        try:
            text = fetch_official_po(edition, mod)
            now_path.write_text(text, encoding="utf-8")
            stats["ok"] += 1
        except Exception as e:
            stats["fail"] += 1
            stats["missing"].append(mod)
            log(f"   ⚠️ {mod}: {e}")
    log(f"   ✅ {stats['ok']} hämtade, {stats['fail']} misslyckades")
    return stats


# ---------------------------------------------------------------------------
# 2) REGLER (apply)
# ---------------------------------------------------------------------------

def load_rules(edition):
    """Läs core.yml + rules/odoo-<edition>.yml; per-version överridar core med samma id."""
    core = yaml.safe_load((RULES_DIR / "core.yml").read_text(encoding="utf-8"))
    terms = {t["id"]: t for t in core.get("terms", [])}

    ver_file = RULES_DIR / f"odoo-{edition.split('.')[0]}.yml"
    if ver_file.exists():
        ver = yaml.safe_load(ver_file.read_text(encoding="utf-8"))
        for t in ver.get("terms", []):
            terms[t["id"]] = t  # överrida hela termen

    return list(terms.values())


def rules_for_module(edition, module, rules):
    """Regler som gäller för utgåva + modul."""
    ver = int(float(edition))
    out = []
    for t in rules:
        versions = t.get("versions", [])
        if ver not in versions:
            continue
        mods = t.get("modules", "*")
        if mods != "*" and module not in mods:
            continue
        out.append(t)
    return out


def rule_pairs(term):
    pairs = [(term["old"], term["new"])]
    pairs += [(v["old"], v["new"]) for v in term.get("variants", [])]
    # längsta match först; stabil sortering för lika längd (ordning i YAML)
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs


def apply_rules_to_str(text, pairs, only_if_msgid=None, msgid=None):
    if not text:
        return text
    if only_if_msgid and msgid is not None and not re.search(only_if_msgid, msgid):
        return text
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new)
    return text


def apply_rules(edition, modules=None):
    """Skapa 'desired' (official-now + regler) per modul → cache/odoo-<ed>/<mod>/desired.po."""
    rules = load_rules(edition)
    log(f"📐 APPLY {edition} — {len(rules)} regler (core + version)")
    stats = {"rules_applied": 0, "phrases_changed": 0}
    for mdir in sorted(edition_cache(edition).iterdir()):
        if not mdir.is_dir():
            continue
        module = mdir.name
        if modules and module not in modules:
            continue
        now_path = mdir / "official-now.po"
        if not now_path.exists():
            continue
        po = polib.pofile(str(now_path))
        rules_mod = rules_for_module(edition, module, rules)
        pairs_by_rule = [(rule_pairs(t), t.get("only_if_msgid")) for t in rules_mod]
        for entry in po:
            for pairs, oim in pairs_by_rule:
                new_str = apply_rules_to_str(entry.msgstr, pairs, oim, entry.msgid)
                if new_str != entry.msgstr:
                    entry.msgstr = new_str
                    stats["phrases_changed"] += 1
                for k in list(entry.msgstr_plural.keys()):
                    new_plural = apply_rules_to_str(entry.msgstr_plural[k], pairs, oim, entry.msgid)
                    if new_plural != entry.msgstr_plural[k]:
                        entry.msgstr_plural[k] = new_plural
                        stats["phrases_changed"] += 1
            if rules_mod:
                stats["rules_applied"] += 1
        po.save(str(mdir / "desired.po"))
    log(f"   ✅ {stats['phrases_changed']} fraser ändrade av regler")
    return stats


# ---------------------------------------------------------------------------
# 3) TREVÄGS-MERGE
# ---------------------------------------------------------------------------

def entry_translation(entry):
    """Översättning som jämförbar sträng: msgstr (eller första icke-tomma pluralform)."""
    if entry.msgstr.strip():
        return entry.msgstr.strip()
    for v in entry.msgstr_plural.values():
        if v.strip():
            return v.strip()
    return ""


def merge_module(edition, module):
    """Klassificera varje fras enligt beslutstabellen. Returnerar dict + statistik."""
    mdir = module_cache(edition, module)
    last_path, now_path, desired_path = mdir / "official-last.po", mdir / "official-now.po", mdir / "desired.po"
    if not now_path.exists():
        return None
    now_po = polib.pofile(str(now_path))
    desired_po = polib.pofile(str(desired_path)) if desired_path.exists() else now_po
    last_po = polib.pofile(str(last_path)) if last_path.exists() else None

    # msgid → entry (första)
    def index(po):
        return {e.msgid: e for e in po}

    now_idx, desired_idx = index(now_po), index(desired_po)
    last_idx = index(last_po) if last_po else {}

    merged = []  # (msgid, klass, official_now, our_will, entry)
    stats = {k: 0 for k in ("override", "converged", "conflict", "new-correct", "new-corrected", "new-ours", "new-manual", "removed", "noop")}

    for msgid, now_e in now_idx.items():
        now = entry_translation(now_e)
        des_e = desired_idx.get(msgid)
        des = entry_translation(des_e) if des_e else now
        last_e = last_idx.get(msgid)
        last = entry_translation(last_e) if last_e else None

        if last is None:  # ny fras
            if des != now:
                if now == "" and des != "":
                    klass = "new-ours"
                else:
                    klass = "new-corrected"
            elif now == "":
                klass = "new-manual"
            else:
                klass = "new-correct"
        elif now == last:  # oförändrad
            if des != now:
                klass = "override"
            else:
                klass = "noop"
        else:  # ändrad av Odoo
            if des == now:
                klass = "converged"
            else:
                klass = "conflict"

        stats[klass] += 1
        merged.append((msgid, klass, now, des, now_e, des_e))

    # Borttagna fraser
    for msgid in last_idx:
        if msgid not in now_idx:
            # Bara relevant om vi tidigare hade en override (desired skiljde sig)
            stats["removed"] += 1
            merged.append((msgid, "removed", "", "", last_idx[msgid], None))

    return {"module": module, "merged": merged, "stats": stats}


# ---------------------------------------------------------------------------
# 4) BYGG
# ---------------------------------------------------------------------------

def build_i18n_extra(module, merged):
    """i18n_extra/sv.po — endast avvikelser (override/conflict/new-ours/new-corrected)."""
    po = polib.POFile()
    po.metadata = {
        "Project-Id-Version": f"odoosa-{module}",
        "POT-Creation-Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "PO-Revision-Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Last-Translator": "odoosa-translate",
        "Language": "sv",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
    }
    keep = {"override", "conflict", "new-ours", "new-corrected"}
    for msgid, klass, now, des, entry, des_entry in merged:
        if klass not in keep:
            continue
        # Skippa tomma/blanksteg msgid — t.ex. modulbeskrivningen som kan
        # ligga som msgid "" + continuation. Sådana entry saknar kommentar och
        # KRASCHAR Odoo 18:s PoFileReader (translate.py:831, AttributeError)
        # eftersom entry.comment blir '' → re.match(r"module[s]?: (\w+)", '') → None.
        if not msgid or not msgid.strip():
            continue
        # Använd vår vilja (desired) — singular som msgstr, plural som msgstr_plural
        if des_entry is not None and des_entry.msgstr_plural:
            new_entry = polib.POEntry(msgid=msgid, msgid_plural=des_entry.msgid_plural,
                                      msgstr_plural=des_entry.msgstr_plural)
        else:
            new_entry = polib.POEntry(msgid=msgid, msgstr=des)
        # Bevara referenser — krav för att Odoo ska applicera översättningen
        # Viktigt: entry.comment får ALDRIG vara tom — Odoo 18 kraschar på
        # entry utan "module[s]: <mod>"-kommentar. Fallback till "module: <mod>".
        new_entry.comment = (entry.comment or "").strip() or f"module: {module}"
        new_entry.tcomment = entry.tcomment
        new_entry.occurrences = entry.occurrences
        new_entry.flags = entry.flags
        new_entry.previous_msgctxt = entry.previous_msgctxt
        po.append(new_entry)
    return po


def content_hash(text):
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def write_if_changed(path, text):
    """Idempotens: skriv bara om innehållet ändrats. Returnerar True om skriven."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def build_edition(edition, modules=None):
    log(f"🏗️  BUILD {edition}")
    out_i18n = BUILD_DIR / f"odoo-{edition}" / "i18n"
    out_extra = BUILD_DIR / f"odoo-{edition}" / "i18n_extra"
    out_diff = BUILD_DIR / f"odoo-{edition}" / "diff"
    report_lines = [f"# odoosa-report — {edition} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    report_lines.append("")
    total = {k: 0 for k in ("override", "converged", "conflict", "new-correct", "new-corrected", "new-ours", "new-manual", "removed", "noop")}

    for mdir in sorted(edition_cache(edition).iterdir()):
        if not mdir.is_dir():
            continue
        module = mdir.name
        if modules and module not in modules:
            continue
        now_path = mdir / "official-now.po"
        if not now_path.exists():
            continue
        res = merge_module(edition, module)
        if res is None:
            continue
        stats = res["stats"]
        for k in total:
            total[k] += stats[k]

        # i18n/sv.po = officiell orörd
        write_if_changed(out_i18n / module / "sv.po", now_path.read_text(encoding="utf-8"))

        # i18n_extra/sv.po = våra avvikelser
        extra = build_i18n_extra(module, res["merged"])
        write_if_changed(out_extra / module / "i18n_extra" / "sv.po", str(extra))

        # diff.po = granskning
        diff = polib.POFile()
        diff.metadata = {"Project-Id-Version": f"odoosa-diff-{module}", "Language": "sv"}
        for msgid, klass, now, des, entry, des_entry in res["merged"]:
            if klass in ("override", "conflict", "new-corrected", "new-ours"):
                if not msgid or not msgid.strip():
                    continue
                d = polib.POEntry(msgid=msgid, msgstr=des)
                d.comment = f"module: {module}"
                d.tcomment = f"{klass} | officiell: {now!r}"
                diff.append(d)
        write_if_changed(out_diff / module / "sv.po", str(diff))

        # Rapportsektion
        report_lines.append(f"## {module}")
        order = [("override", "override"), ("converged", "converged 🎉"), ("conflict", "conflict ⚠️"),
                 ("new-correct", "ny (redan rätt)"), ("new-corrected", "ny (korrigerad)"),
                 ("new-ours", "ny (vår)"), ("new-manual", "ny (manuell)"), ("removed", "borttagen"), ("noop", "oförändrad")]
        for key, label in order:
            report_lines.append(f"- {label}: {stats[key]}")
        # Sampel
        for msgid, klass, now, des, entry, des_entry in res["merged"]:
            if klass in ("override", "conflict"):
                report_lines.append(f"  · [{klass}] {msgid[:60]} → {des[:40]!r}")
                break

    report_lines.insert(1, f"\n**Totalt:** {total}")
    report_path = REPORTS_DIR / f"odoosa-{edition}-report.md"
    write_if_changed(report_path, "\n".join(report_lines) + "\n")
    log(f"   ✅ i18n + i18n_extra + diff + rapport skrivna ({len([p for p in (out_extra).glob('*/sv.po')])} moduler)")
    return total


# ---------------------------------------------------------------------------
# REGRESSION (task 1.4) — byggresultat vs gamla snapshot
# ---------------------------------------------------------------------------

def regression(edition):
    """Jämför önskat resultat (official-now + regler) mot gamla odoo-<edition>-<mod>-sv.po."""
    log(f"🔬 REGRESSION {edition}")
    major = edition.split(".")[0]
    snapshots = sorted(ROOT.glob(f"odoo-{major}-*-sv.po"))
    if not snapshots:
        log("   ⚠️ inga snapshot-filer hittade i repo-roten")
        return
    rules = load_rules(edition)
    for snap in snapshots:
        module = snap.name.replace(f"odoo-{major}-", "").replace("-sv.po", "")
        mdir = module_cache(edition, module)
        now_path = mdir / "official-now.po"
        if not now_path.exists():
            log(f"   ⚠️ {module}: ingen official-now (kör fetch först)")
            continue
        snap_po = polib.pofile(str(snap))
        now_po = polib.pofile(str(now_path))
        rules_mod = rules_for_module(edition, module, rules)
        pairs_by_rule = [(rule_pairs(t), t.get("only_if_msgid")) for t in rules_mod]

        # Beräkna "vår vilja" för snapshot-msgid:er
        match = 0
        mismatch = 0
        samples = []
        snap_idx = {e.msgid: e for e in snap_po}
        for msgid, snap_e in snap_idx.items():
            snap_tr = entry_translation(snap_e)
            if not snap_tr:
                continue  # oöversatt i snapshot — ingen jämförelse
            now_e = now_po.find(msgid)
            now_tr = entry_translation(now_e) if now_e else ""
            ours = now_tr
            for pairs, oim in pairs_by_rule:
                ours = apply_rules_to_str(ours, pairs, oim, msgid)
            if ours == snap_tr:
                match += 1
            else:
                mismatch += 1
                if len(samples) < 5:
                    samples.append((msgid[:50], ours[:30], snap_tr[:30]))
        pct = 100.0 * match / (match + mismatch) if (match + mismatch) else 100.0
        log(f"   {module}: {match} match / {mismatch} mismatch ({pct:.1f}%)")
        for s in samples:
            log(f"     · {s[0]}: vi={s[1]!r} snapshot={s[2]!r}")


# ---------------------------------------------------------------------------
# CHECK-EDITION (task 2.5) — ny-utgåva-procedur
# ---------------------------------------------------------------------------

def check_edition(edition):
    """Verifiera att utgåvan har native i18n_extra-stöd (get_po_paths)."""
    log(f"🔎 CHECK-EDITION {edition}")
    url = f"{RAW}/{edition}/odoo/tools/translate.py"
    try:
        text = fetch_raw(url)
    except Exception as e:
        log(f"   ❌ {edition} verkar inte finnas / ej nåbar: {e}")
        return 1
    if "i18n_extra" in text and "get_po_paths" in text:
        log("   ✅ native i18n_extra-stöd bekräftat (get_po_paths innehåller i18n_extra)")
        return 0
    log("   ⚠️ i18n_extra INTE hittat i get_po_paths — granska mekanismen innan lane aktiveras!")
    return 1


# ---------------------------------------------------------------------------
# PUBLISH — commit + push till GitHub (task 4.1)
# ---------------------------------------------------------------------------

PUBLISH_KEY = "/root/.ssh/odoosa_translate"


def git(cmd, cwd=None, check=True):
    import subprocess
    env = None
    if Path(PUBLISH_KEY).exists():
        env = {"GIT_SSH_COMMAND": f"ssh -i {PUBLISH_KEY} -o IdentitiesOnly=yes"}
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True,
                       env=env, timeout=300)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(cmd)} misslyckades: {r.stderr.strip()[:500]}")
    return r


def publish(dry_run=False, message=None):
    """Commit + push byggartefakter, regler, ordlista och pipeline till GitHub.
    Körs av arbetsminionen (enda maskinen som arbetar med GitHub)."""
    import subprocess
    log("📤 PUBLISH — commit + push till github.com/vertelab/odoosa-translate")

    # Git-identitet (om ej satt)
    git(["git", "config", "user.name"], check=False)
    if git(["git", "config", "user.name"], check=False).returncode != 0:
        git(["git", "config", "user.name", "odoosa-translate bot"])
    if git(["git", "config", "user.email"], check=False).returncode != 0:
        git(["git", "config", "user.email", "odoosa@vertel.se"])

    # Stega: artefakter + regler + ordlista + pipeline + rapporter + docs
    git(["git", "add", "-A", "build/", "reports/", "rules/", "glossary.csv",
         "odoosa.py", "odoo18-sv-translations.txt", "README.md", "docs/", ".gitignore"])

    staged = git(["git", "diff", "--cached", "--name-only"], check=False).stdout.strip()
    if not staged:
        log("   ℹ️ inga ändringar att publicera")
        return 0

    n = len(staged.splitlines())
    default_msg = f"odoosa sync — {datetime.now().strftime('%Y-%m-%d %H:%M')} ({n} filer)"
    msg = message or default_msg
    git(["git", "commit", "-m", msg])
    log(f"   ✅ commit: {msg}")

    if dry_run:
        log("   🛑 dry-run — push skippad")
        return 0

    # Push via SSH deploy key (explicit URL — origin är HTTPS för read)
    ssh_url = "git@github.com:vertelab/odoosa-translate.git"
    git(["git", "push", ssh_url, "HEAD"])
    log(f"   ✅ push till {ssh_url} klar")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_versions(arg):
    return [v.strip() for v in arg.split(",") if v.strip()] if arg else DEFAULT_VERSIONS


def parse_modules(arg):
    return [m.strip() for m in arg.split(",") if m.strip()] if arg else None


def main():
    ap = argparse.ArgumentParser(description="odoosa — Odoo SA translation pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("fetch", "apply", "merge", "build", "run", "regression"):
        p = sub.add_parser(name)
        p.add_argument("--versions", default=",".join(DEFAULT_VERSIONS))
        p.add_argument("--modules", default=None, help="komma-separerad lista (test/dev)")
    pub = sub.add_parser("publish")
    pub.add_argument("--message", default=None)
    pub.add_argument("--dry-run", action="store_true")
    ce = sub.add_parser("check-edition")
    ce.add_argument("edition")

    args = ap.parse_args()
    versions = parse_versions(args.versions) if hasattr(args, "versions") else None
    modules = parse_modules(args.modules) if hasattr(args, "modules") else None

    if args.cmd == "fetch":
        for v in versions:
            fetch_edition(v, modules)
    elif args.cmd == "apply":
        for v in versions:
            apply_rules(v, modules)
    elif args.cmd == "merge":
        for v in versions:
            build_edition(v, modules)  # merge sker i bygg-steget (rapport/artefakter)
    elif args.cmd == "build":
        for v in versions:
            build_edition(v, modules)
    elif args.cmd == "run":
        for v in versions:
            fetch_edition(v, modules)
            apply_rules(v, modules)
            build_edition(v, modules)
    elif args.cmd == "publish":
        sys.exit(publish(dry_run=args.dry_run, message=args.message))
    elif args.cmd == "regression":
        for v in versions:
            regression(v)
    elif args.cmd == "check-edition":
        sys.exit(check_edition(args.edition))


if __name__ == "__main__":
    main()
