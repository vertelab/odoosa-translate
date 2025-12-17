#!/usr/bin/python3
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import base64
import polib
import re
import requests
import subprocess 
import traceback

def detect_local_odoo_version():
        """Kör `odoo-bin --version` och matchar mot upptäckta versioner."""
        try:
            result = subprocess.run(["odoo-bin", "--version"], 
                                  capture_output=True, text=True, timeout=10)
        except Exception as e:
            try:
                result = subprocess.run(["odoo", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            except Exception as e:
                print(f"Kunde inte köra odoo-bin: {e}")
                return None
        local_match = re.search(r'(\d+(?:\.\d+)?)', result.stdout)
        if local_match:
            major,minor =local_match.group(1).split('.')
            return f"odoo-{major}-"
        return None


class GithubPofile:
    def __init__(self, owner: str = "vertelab", repo: str = "odoosa-translate", branch: str = "main",odoo: str = ""):
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.odoo_version = odoo
        self.odoo_base_path = Path('/usr/share/core-odoo/addons')
        
    def fetch_repo_tree(self) -> List[Dict[str, str]]:
        """Hämtar hela repo-trädet med filer och SHA."""
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees/{self.branch}?recursive=1"
        try:
            resp = requests.get(url)
        except Exception as e:
            print(f"❌ Fel fetch_repo_tree {url}: {e}")
            return []
        resp.raise_for_status()
        data = resp.json()
        result = []
        po_pattern = re.compile(r'^odoo-\d+(?:-\d+)?-([^-]+)(?:-[^-]+)?\.po$', re.IGNORECASE)
        for item in [ item for item in data.get("tree", []) 
                        if item["type"] == "blob" and self.odoo_version in item["path"] and item["path"].endswith(".po")]:
            match = po_pattern.search(item["path"])
            if match:
                result.append({
                    "path": item["path"],
                    "sha": item["sha"],
                    "module": match.group(1),
                    'file': 'sv.po',
                })
        return result
        
    def update_local_file(self, file_json):
        # Lokal filväg: /usr/share/core-odoo/addons/module/i18n/sv.po
        # ~ local_path = f"{self.odoo_base_path}/{file_json['module']}/i18n/{file_json['file']}"
        local_path = self.odoo_base_path / file_json['module'] / "i18n" / file_json['file']
        if local_path.exists():
            try:
                # Läs lokal .po-fil
                local_po = polib.pofile(str(local_path))
                po_file = polib.pofile(self._get_blob_content(file_json["sha"]))
                # ~ print(f"{po_file=}")
                # ~ exit()
                updated = False
                for diff_entry in po_file:
                    if diff_entry.msgstr and diff_entry.msgstr.strip():
                        local_entry = local_po.find(str(diff_entry.msgid))
                        if local_entry:
                            if str(local_entry.msgstr) != str(diff_entry.msgstr):
                                local_entry.msgstr = diff_entry.msgstr
                                updated = True
                        else:
                            # Lägg till ny entry
                            new_entry = polib.POEntry(
                                msgid=diff_entry.msgid,
                                msgstr=diff_entry.msgstr
                            )
                            local_po.append(new_entry)
                            updated = True
                
                if updated:
                    # Spara uppdaterad lokal fil
                    local_po.save(str(local_path))
                    print(f"✅ Uppdaterade {local_path} ({len(po_file)} fraser)")
            except Exception as e:
                print(f"❌ Fel vid uppdatering {local_path}: {e}\n{traceback.print_exc()}")
        else:
            print(f"⚠️  Lokal fil saknas: {local_path}")
    
    def _get_blob_content(self, sha: str) -> str:
        """Hämtar och dekodar blob-innehåll."""
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/blobs/{sha}"
        try:
            resp = requests.get(url)
        except Exception as e:
            print(f"❌ Fel get {url}: {e}")
        resp = requests.get(url)
        resp.raise_for_status()
        blob = resp.json()
        # ~ print(str(base64.b64decode(blob["content"]).decode("utf-8")))
        return str(base64.b64decode(blob["content"]).decode("utf-8"))
        return base64.b64decode(blob['content'].replace("\n", "")).decode("utf-8", errors="replace")




if __name__ == "__main__":
    
    # ~ parser = argparse.ArgumentParser(
        # ~ description="Sync .po files and ower write changes to Odoo-core."
    # ~ )
    # ~ parser.add_argument("-s", "--source", required=True,
                        # ~ help="Source file (original .po)")
    # ~ parser.add_argument("-t", "--target", required=True,
                        # ~ help="Target file (edited .po)")
    # ~ parser.add_argument("-o", "--output",
                        # ~ help="Output file (.po) with changes (default: stdout)")
    # ~ return parser.parse_args()
    
    
    odoo = detect_local_odoo_version()
    github = GithubPofile(owner='vertelab',repo='odoosa-translate',branch='main',odoo=odoo)
    for file in github.fetch_repo_tree():
        github.update_local_file(file)
    
