#!/usr/bin/python3
import base64
from pathlib import Path
import argparse
import os
import polib
import re
import subprocess 
import sys
import requests
import wlc

def detect_odoo_version() -> str:
    """Hämtar Odoo-version från server."""
    try:
        result = subprocess.run(["odoo-bin", "--version"], capture_output=True, text=True, timeout=10)
        match = re.search(r'(\d+)', result.stdout)
        if match:
            return f"odoo-{match.group(1)}"
    except:
        pass
    try:
        result = subprocess.run(["odoo", "--version"], capture_output=True, text=True, timeout=10)
        match = re.search(r'(\d+)', result.stdout)
        if match:
            return f"odoo-{match.group(1)}"
    except:
        pass
    print("❌ Kunde inte hitta Odoo version!")
    return "odoo-18"  # Fallback

def get_github_po_files(owner="vertelab", repo="odoosa-translate", branch="main") -> list[Dict]:
    """Hämtar alla odoo-*-*.po filer från GitHub."""
    version = detect_odoo_version()
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    files = []
    pattern = re.compile(rf'^{version}-([a-z0-9_-]+)-sv\.po$')
    
    for item in data["tree"]:
        if item["type"] == "blob" and item["path"].endswith(".po"):
            match = pattern.search(item["path"])
            if match:
                files.append({
                    "path": item["path"],
                    "sha": item["sha"],
                    "module": match.group(1)
                })
    
    print(f"✅ Hittade {len(files)} filer för {version}: {', '.join(f['module'] for f in files)}")
    return files

def download_github_po(sha: str, owner="vertelab", repo="odoosa-translate") -> str:
    """Laddar ner .po från GitHub via SHA."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{sha}"
    resp = requests.get(url)
    resp.raise_for_status()
    blob = resp.json()
    content = base64.b64decode(blob["content"]).decode("utf-8")
    return content

def download_weblate_po(version: str, module: str, token: str) -> str:
    """Laddar ner .po från Weblate."""
    url = f"https://translate.odoo.com/api/translations/{version}/{module}/sv/file/"
    headers = {"Authorization": f"Token {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.text

def update_local_po(github_po_content: str, weblate_po_content: str, local_path: Path) -> bool:
    """Uppdaterar lokal Odoo-fil: GitHub-översättningar > Weblate."""
    try:
        github_po = polib.pofile(github_po_content)
        weblate_po = polib.pofile(weblate_po_content)
        local_po = polib.pofile(str(local_path)) if local_path.exists() else polib.POFile()
        
        updated = False
        for entry in github_po:
            if entry.msgstr.strip():  # Endast översatta
                local_entry = local_po.find(entry.msgid)
                if local_entry:
                    if local_entry.msgstr.strip() != entry.msgstr.strip():
                        local_entry.msgstr = entry.msgstr
                        updated = True
                else:
                    local_po.append(entry)
                    updated = True
        
        if updated:
            local_po.save(str(local_path))
            print(f"✅ Uppdaterade {local_path}")
            return True
        print(f"ℹ️ Inga ändringar: {local_path}")
        return False
    except Exception as e:
        print(f"❌ Fel {local_path}: {e}")
        return False

def main():
    version = detect_odoo_version()
    token = os.environ.get('ODOO_API_KEY')
    if not token:
        print("❌ Sätt ODOO_API_KEY!")
        return
    
    core_path = Path('/usr/share/core-odoo/addons')
    github_files = get_github_po_files()
    
    for file_info in github_files:
        module = file_info['module']
        print(f"\n🔄 Bearbetar {module}...")
        
        # 1. Ladda GitHub-fil
        github_po = download_github_po(file_info['sha'])
        
        # 2. Ladda Weblate-fil
        weblate_po = download_weblate_po(version, module, token)
        
        # 3. Uppdatera lokal Odoo-fil
        local_path = core_path / module / "i18n" / "sv.po"
        update_local_po(github_po, weblate_po, local_path)

if __name__ == "__main__":
    main()
