#!/usr/bin/python3
import argparse
import base64
import requests
from pathlib import Path
import polib
import re
import subprocess
import sys
import os
from datetime import datetime
import time


def compare_official_vs_github(official_str, github_str, version, module):
    """Jämför OFFICIELL Odoo vs DIN GitHub - NOTERA förändringar."""
    diff_dir = Path('/usr/share/odoosa-translate')
    
    try:
        official_po = polib.pofile(official_str)
        github_po = polib.pofile(github_str)
        
        # NYA i Odoo (saknas i din GitHub)
        new_in_official = []
        # TA bort från din GitHub (saknas i Odoo)
        removed_from_github = []
        # Ändrade i Odoo
        changed_in_official = []
        
        github_dict = {e.msgid: e for e in github_po}
        official_dict = {e.msgid: e for e in official_po}
        
        print(f"🔍 {module}: OFFICIELL vs DIN GitHub")
        
        # NYA i Odoo!
        for msgid, entry in official_dict.items():
            if msgid not in github_dict:
                new_in_official.append(entry.msgid)
        
        # Borttagna från din GitHub!
        for msgid in github_dict:
            if msgid not in official_dict:
                removed_from_github.append(msgid)
        
        # Ändrade msgstr!
        for msgid, github_entry in github_dict.items():
            if msgid in official_dict:
                official_entry = official_dict[msgid]
                if (official_entry.msgstr.strip() != github_entry.msgstr.strip() and 
                    github_entry.msgstr.strip()):
                    changed_in_official.append((msgid, github_entry.msgstr, official_entry.msgstr))
        
        # SKAPA rapport-fil!
        report_path = diff_dir / f"{version}-{module}-changes.po"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# ODOO OFFICIELLA ÄNDRINGAR vs DIN GitHub\n")
            f.write(f"# Modul: {module} - {datetime.now()}\n\n")
            
            if new_in_official:
                f.write(f"# 🆕 NYA i Odoo ({len(new_in_official)}):\n")
                for msgid in new_in_official[:10]:  # Första 10
                    f.write(f'#: msgid "{msgid[:60]}"\n')
                f.write("\n")
            
            if removed_from_github:
                f.write(f"# 🗑️ BORTTAGNA från din GitHub ({len(removed_from_github)}):\n")
                for msgid in removed_from_github[:10]:
                    f.write(f'#: msgid "{msgid[:60]}"\n')
                f.write("\n")
            
            if changed_in_official:
                f.write(f"# 🔄 ÄNDRade i Odoo ({len(changed_in_official)}):\n")
                for msgid, din, odoo in changed_in_official[:5]:
                    f.write(f'#: msgid "{msgid[:50]}"\n')
                    f.write(f'# DIN: "{din[:30]}" → ODOO: "{odoo[:30]}"\n')
        
        print(f"📋 RAPPORT: {report_path}")
        print(f"   🆕 NYA i Odoo: {len(new_in_official)}")
        print(f"   🗑️ Borttagna: {len(removed_from_github)}")
        print(f"   🔄 Ändrade: {len(changed_in_official)}")
        
        return {
            'new': new_in_official,
            'removed': removed_from_github,
            'changed': changed_in_official,
            'report_path': report_path
        }
        
    except Exception as e:
        print(f"⚠️ Jämförelsefel {module}: {e}")
        return None

def detect_odoo_version():
    """Auto-detekt Odoo version."""
    for cmd in ["odoo-bin --version", "odoo --version"]:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
            match = re.search(r'(\d+)', result.stdout)
            if match:
                return f"odoo-{match.group(1)}"
        except:
            pass
    return "odoo-18"

def find_github_files(version):
    """Hämtar alla odoo-*-*.po från GitHub API."""
    url = "https://api.github.com/repos/vertelab/odoosa-translate/git/trees/main?recursive=1"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    files = []
    pattern = re.compile(rf'^{version}-([a-z0-9_-]+)-sv\.po$')
    
    for item in data["tree"]:
        if item["type"] == "blob" and pattern.search(item["path"]):
            match = pattern.search(item["path"])
            files.append({
                'path': item["path"],
                'module': match.group(1),
                'sha': item["sha"]
            })
    
    print(f"✅ GitHub: {len(files)} filer: {[f['module'] for f in files]}")
    return files

def download_github_po(sha):
    """GitHub .po med rate limit hantering."""
    url = f"https://api.github.com/repos/vertelab/odoosa-translate/git/blobs/{sha}"
    for attempt in range(3):
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            blob = resp.json()
            return base64.b64decode(blob["content"]).decode("utf-8")
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 403:
                print(f"⏳ GitHub rate limit! Väntar {60*attempt+10}s...")
                time.sleep(60*attempt + 10)
                continue
            raise
    raise Exception("GitHub rate limit - prova igen om 1h!")

def download_official_odoo_po(version, module):
    """Ladda OFFICIELL Odoo sv.po från GitHub - DYNAMISK version."""
    odoo_version = version.replace("odoo-", "") + ".0"
    url = f"https://raw.githubusercontent.com/odoo/odoo/{odoo_version}/addons/{module}/i18n/sv.po"
    
    print(f"   🌐 OFFICIELL: {module}")
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        
        diff_dir = Path('/usr/share/odoosa-translate')
        official_path = diff_dir / f"{version}-{module}-official.po"
        
        with open(official_path, 'w', encoding='utf-8') as f:
            f.write(resp.text)
        
        print(f"      ✅ {official_path.name}")
        return resp.text
        
    except Exception as e:
        print(f"      ⚠️ OFFICIELL {module}: {e}")
        return None

def sync_odoo(github_str, module):
    """Synkar till core-odoo."""
    local_path = Path('/usr/share/core-odoo/addons') / module / 'i18n' / 'sv.po'
    github_po = polib.pofile(github_str)
    
    translated = len([e for e in github_po if e.msgstr.strip()])
    github_po.save(str(local_path))
    print(f"✅ SYNC: {translated} översättningar → {local_path}")


def git_commit_and_push(repo_dir="/usr/share/core-odoo"):
    """Commitar och pushar översättningar automatiskt till repo."""
    try:
        print("📤 PUSHA ändringar till git...")
        subprocess.run(["git", "-C", repo_dir, "add", "."], check=True)
        msg = f"Auto-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "-C", repo_dir, "commit", "-m", msg], check=True)
        subprocess.run(["git", "-C", repo_dir, "push"], check=True)
        print("✅ Git push klar!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git-fel: {e}")
    except Exception as ex:
        print(f"⚠️ Kunde inte pusha till git: {ex}")
        

def create_diff_always(github_str, official_str, version, module):
    """Diff mot OFFICIELL Odoo."""
    diff_dir = Path('/usr/share/odoosa-translate')
    diff_dir.mkdir(exist_ok=True)
    
    try:
        github_po = polib.pofile(github_str)
        official_po = polib.pofile(official_str) if official_str else polib.POFile()
        
        diff_po = polib.POFile()
        changes = []
        
        print(f"🔍 {module}: {len(github_po)} DIN vs {len(official_po)} OFFICIELL")
        
        for entry in github_po:
            if entry.msgstr.strip():
                official_entry = official_po.find(entry.msgid)
                if (not official_entry or 
                    official_entry.msgstr.strip() != entry.msgstr.strip()):
                    orig_str = official_entry.msgstr.strip() if official_entry and official_entry.msgstr.strip() else "(saknas)"
                    changes.append((entry.msgid, orig_str, entry.msgstr))
                    diff_entry = polib.POEntry(msgid=entry.msgid, msgstr=entry.msgstr)
                    diff_po.append(diff_entry)
        
        if changes:
            diff_po.metadata = {
                'Project-Id-Version': f'{version}-{module}',
                'POT-Creation-Date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'PO-Revision-Date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'Last-Translator': 'odoosa-translate',
                'Language': 'sv',
                'MIME-Version': '1.0',
                'Content-Type': 'text/plain; charset=UTF-8'
            }
            
            diff_path = diff_dir / f"{version}-{module}-diff.po"
            diff_po.save(str(diff_path))
            print(f"📄 DIFF: {diff_path} ({len(changes)} ÄNDRINGAR)")
            print("📋 ÄNDRINGAR:")
            for msgid, orig, din in changes[:3]:
                print(f"   {msgid[:40]:40} | {orig[:15]:15} → {din[:15]}")
        else:
            print(f"ℹ️ Inga skillnader {module}")
            
    except Exception as e:
        print(f"⚠️ Skip diff {module}: {str(e)[:60]}")

def main():
    import os
    parser = argparse.ArgumentParser(description="Odoo-översättningsscript")
    parser.add_argument("--auto", action="store_true", help="Kör allt utan frågor")
    parser.add_argument("--no-sync", action="store_true", help="Hoppa över sync + git push")
    args = parser.parse_args()
   
    if os.geteuid() != 0:
        print("🔒 Kräver sudo...")
        os.execvp("sudo", ["sudo", sys.executable, __file__])
    
    print("🚀 ODOSUPER: OFFICIELL + DIFF → SYNC!")
    version = detect_odoo_version()
    print(f"📦 Odoo version: {version}")
    
    files = find_github_files(version)
    print(f"\n{'='*60}")
    print(f"🚀 OFFICIELL + DIFF för {len(files)} moduler!\n")
    
    # SKAPA + RENSA diff-mapp - ALLA filer!
    diff_dir = Path('/usr/share/odoosa-translate')
    diff_dir.mkdir(exist_ok=True)

    old_files = list(diff_dir.glob('*'))
    if old_files:
        for old_file in old_files:
            old_file.unlink()
        print(f"🧹 RENSAT {len(old_files)} gamla filer - NY START!")
    else:
        print("🧹 Mapp tom - kör igång!")

    # STEG 0: Ladda OFFICIELLA Odoo-filer
    print(f"\n{'='*60}")
    print("🌐 STEG 0: LADDAR OFFICIELLA ODOO-FILER...")
    official_files = {}
    
    for file_info in files:
        module = file_info['module']
        official_str = download_official_odoo_po(version, module)
        if official_str:
            official_files[module] = official_str
    
    # STEG 1: SKAPA DIFF-FILER
    print(f"\n{'='*60}")
    print("📋 STEG 1: SKAPAR DIFF-FILER...")
    github_files = {}
    
    for file_info in files:
        module = file_info['module']
        print(f"{'='*50}")
        print(f"🔄 MODUL: {module}")
        
        github_str = download_github_po(file_info['sha'])
        create_diff_always(github_str, official_files.get(module), version, module)
        github_files[module] = github_str
        print()
    
    # VISA DIFF-FILER
    print(f"\n{'='*60}")
    print("📂 DIFF-FILER SKAPADE:")
    diff_count = 0
    for diff_file in diff_dir.glob('*.po'):
        size = diff_file.stat().st_size
        print(f"   📄 {diff_file.name} ({size/1000:.1f} KB)")
        diff_count += 1
    
    if diff_count == 0:
        print("ℹ️ Inga ändringar → hoppar över sync!")
        return
    
    # STEG 2: Jämför OFFICIELL vs DIN GitHub
    print(f"\n{'='*60}")
    print("🔍 STEG 2: OFFICIELLA ODOO ÄNDRINGAR...")
    changes_summary = {}

    for file_info in files:
        module = file_info['module']
        if module in official_files and module in github_files:
            print(f"{'='*50}")
            print(f"🔍 JÄMFÖR: {module}")
            changes = compare_official_vs_github(
                official_files[module], 
                github_files[module], 
                version, 
                module
            )
            if changes:
                changes_summary[module] = changes

    # FRÅGA OM DU VILL REDIGERA!
    print(f"\n{'='*60}")
    if not args.auto:
        print("❓ ODOO har ÄNDRINGAR! Vill du redigera dina filer först? (y/n)")
        edit_answer = input("→ ").lower().strip()
    else:
        edit_answer = 'n'

    if edit_answer in ['y', 'ja', 'yes', 'j']:
        print("\n⏳ ÖPPNA rapport-filer i PoEdit och redigera dina GitHub-filer!")
        print(f"📂 Kolla: {diff_dir}/odoo-18-*-changes.po")
        print("Kör scriptet igen när du är klar!")
        return  # Avbryt - du redigerar manuellt!

    # Fortsätt med sync-frågan...

    # FRÅGA OM SYNC
    print(f"\n{'='*60}")
    if not args.auto:
        print("❓ SKA SYNCA dina ändringar till Odoo? (y/n)")
        answer = input("→ ").lower().strip()
    else:
        answer = "y" if not args.no_sync else "n"


    
    if answer in ['y', 'ja', 'yes', 'j']:
        print("\n🚀 STEG 2: SYNKAR till Odoo...")
        for module, github_str in github_files.items():
            print(f"{'='*50}")
            print(f"🔄 SYNC: {module}")
            sync_odoo(github_str, module)
        print("✅ ALLT SYNkat!")
        if not args.no_sync:
            git_commit_and_push()
    else:
        print("⏹️ Sync avbruten - filer kvar för kontroll!")
    
    print(f"\n📂 Filer finns här: {diff_dir}")

if __name__ == "__main__":
    main()
