#!/usr/bin/python3
from pathlib import Path
import argparse
import os
import polib
import re
import subprocess 
import sys
import wlc

def get_module_name(filename_path):
    # ~ pattern = r'# This file contains the translation of the following modules:[\s\n]*# \*(.+?)[\s\n]'
    pattern = r'#\s*This file contains the translation of the following modules:[\s\S]*?#\s*\*\s*([a-zA-Z0-9_-]+)'
    
    with open(filename_path, 'r') as f:
        content = f.read()
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            modules = [m.strip() for m in match.group(1).split(',')]
            print(modules)
            return modules[0]


class WeblateWLCClient:
    def __init__(self, base_url="https://translate.odoo.com/api/", api_token=None):
        if not api_token:
            logger.warning("No Weblate API token provided. Some operations may be restricted.")
        self.api_token = api_token
        self.client = wlc.Weblate(url=base_url, key=api_token)

    def download_po_file(self, project_slug, component_slug, language_code):
        headers = {'Accept': 'application/x-gettext'}
        if self.api_token:
            headers['Authorization'] = f'Token {self.api_token}'
        url = f"{self.client.url}translations/{project_slug}/{component_slug}/{language_code}/file/"
        r = self.client.session.get(url, headers=headers)
        r.raise_for_status()
        print(f"{r.content}")
        return r.content.decode("utf-8")
        return str(base64.b64decode(r.content).decode("utf-8"))

    def download_glossary(self, project_slug, component_slug, language_code, file_type='tbx'):        
        # Lägg till token i headern så att API tillåter hämtning
        headers = {'Accept': 'application/x-gettext'}
        if self.api_token:
            headers['Authorization'] = f'Token {self.api_token}'
        url = f"{self.client.url}translations/{project_slug}/{component_slug}/{language_code}/file/"
        r = self.client.session.get(url, headers=headers)
        r.raise_for_status()
        with open('glossary.tbx', "wb") as f:
            f.write(r.content)
        if file_type == 'csv':
            self._convert_tbx_to_csv('glossary.tbx','glossary.csv',source_lang='en',target_lang=language_code)
            os.remove('glossary.tbx')
            logger.info(f"Downloaded: glossary.csv")
        else:
            logger.info(f"Downloaded: glossary.tbx")
        return 'glossary'

    def _convert_tbx_to_csv(self, tbx_path, csv_path, source_lang="en", target_lang="sv"):
        """
        Konverterar TBX (MARTIF XML) till CSV med kolumner 'source', 'target'
        """
        tree = ET.parse(tbx_path)
        root = tree.getroot()

        # TBX använder ofta XML-namnrymder, men vi kan matcha utan via .tag.endswith
        rows = []
        for term_entry in root.findall(".//termEntry"):
            src_term = None
            tgt_term = None
            for lang_set in term_entry.findall("langSet"):
                lang = lang_set.get("{http://www.w3.org/XML/1998/namespace}lang")
                term_elem = lang_set.find(".//term")
                if term_elem is not None:
                    if lang.lower() == source_lang.lower():
                        src_term = term_elem.text
                    elif lang.lower() == target_lang.lower():
                        tgt_term = term_elem.text
            if src_term and tgt_term:
                rows.append((src_term, tgt_term))

        # Skriv CSV
        with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["source", "target"])
            writer.writerows(rows)


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
            return f"odoo-{major}"
        return None


def build_output_po(source_po, target_po):
    """
    Build a new POFile with all changes made in target compared to source
    (same msgid but changed msgstr, plus new msgids).
    """
    out_po = polib.POFile()

    # Copy metadata from target (optional but often desirable)
    out_po.metadata = target_po.metadata.copy()

    # Fast lookup table for source
    source_index = {e.msgid: e for e in source_po}

    # Iterate through all entries in target
    for t_entry in target_po:
        s_entry = source_index.get(t_entry.msgid)

        if s_entry is None:
            # New string in target -> include it
            out_po.append(polib.POEntry(
                msgid=t_entry.msgid,
                msgstr=t_entry.msgstr,
                msgctxt=t_entry.msgctxt,
                occurrences=t_entry.occurrences,
                flags=t_entry.flags,
                comment=t_entry.comment,
                tcomment=t_entry.tcomment,
            ))
        else:
            # Exists in source: include only if msgstr has changed
            if (t_entry.msgstr or "").strip() != (s_entry.msgstr or "").strip():
                out_po.append(polib.POEntry(
                    msgid=t_entry.msgid,
                    msgstr=t_entry.msgstr,
                    msgctxt=t_entry.msgctxt,
                    occurrences=t_entry.occurrences,
                    flags=t_entry.flags,
                    comment=t_entry.comment,
                    tcomment=t_entry.tcomment,
                ))

    return out_po

def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare two .po files and write a third with changes from target."
    )
    #parser.add_argument("-m", "--module", required=True,help="Module to work with")
    parser.add_argument("-p", "--pofile", required=True,help="Pofile with better translation")
    #parser.add_argument("-v", "--version", required=True,help="Odoo version major.minor eg 18.0")
    parser.add_argument('--url', '-u', default='https://translate.odoo.com/api/')
    parser.add_argument("-o", "--output", action="store_true",
                        help="Output file (.po) with changes (default: stdout)")
    return parser.parse_args()

def main():
    args = parse_args()
    
    url = "https://translate.odoo.com/api/"
    token = os.environ.get('ODOO_API_KEY')
    glossary_project='odoo-glossaries'
    glossary_component='odoo-main-glossary'

    client = WeblateWLCClient(url, token)
    
    module = get_module_name(args.pofile)
    print(f"{module=}")
    source_path = client.download_po_file(detect_local_odoo_version(), module, 'sv')
    target_path = Path(args.pofile)

    if not target_path.exists():
        raise SystemExit(f"Pofile missing: {target_path}")

    source_po = polib.pofile(source_path)
    target_po = polib.pofile(str(target_path))

    out_po = build_output_po(source_po, target_po)

    if args.output:
        output_path = f"{detect_local_odoo_version()}-{module}-sv.po"
        out_po.save(str(output_path))
        print(f"Wrote {len(out_po)} entries to {output_path}", file=sys.stderr)
    else:
        # Write PO content directly to stdout
        sys.stdout.write(str(out_po))
        print(f"\nWrote {len(out_po)} entries to stdout", file=sys.stderr)

if __name__ == "__main__":
    main()
