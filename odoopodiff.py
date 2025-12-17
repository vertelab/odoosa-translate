#!/usr/bin/python3
import argparse
import polib
import sys
import re
import subprocess 
from pathlib import Path

def get_module_name(filename_path):
    pattern = r'# This file contains the translation of the following modules:[\s\n]*# \*(.+?)[\s\n]'
 
    with open(filename_path, 'r') as f:
        content = f.read()
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            modules = [m.strip() for m in match.group(1).split(',')]
            return modules[0]


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
    parser.add_argument("-o", "--output", action="store_true",
                        help="Output file (.po) with changes (default: stdout)")
    return parser.parse_args()

def main():
    args = parse_args()
    module = get_module_name(args.pofile)
    source_path = Path(f"/usr/share/core-odoo/addons/{module}/i18n/sv.po")
    target_path = Path(args.pofile)

    if not source_path.exists():
        raise SystemExit(f"Source file missing: {source_path}")
    if not target_path.exists():
        raise SystemExit(f"Pofile missing: {target_path}")

    source_po = polib.pofile(str(source_path))
    target_po = polib.pofile(str(target_path))

    out_po = build_output_po(source_po, target_po)

    if args.output:
        output_path = f"{detect_local_odoo_version()}{module}-sv.po"
        out_po.save(str(output_path))
        print(f"Wrote {len(out_po)} entries to {output_path}", file=sys.stderr)
    else:
        # Write PO content directly to stdout
        sys.stdout.write(str(out_po))
        print(f"\nWrote {len(out_po)} entries to stdout", file=sys.stderr)

if __name__ == "__main__":
    main()
