#!/usr/bin/env python3

# jakob@odooutv18:~$ chmod +x check_module_name_in_po_file.py 
# jakob@odooutv18:~$ sudo ./check_module_name_in_po_file.py 
# Kontrollerar .po-filer...
#
# Totalt 376 filer hittade
# 376 OK
# 0 med fel
#
# jakob@odooutv18:~$ 

import os
import glob
import fnmatch
from pathlib import Path

def extract_module_name(line):
    """Extraherar modulnamn efter * på raden."""
    if '*' in line:
        return line.split('*', 1)[1].strip().split()[0] if line.split('*', 1)[1].strip() else None
    return None

def check_po_files():
    results = []
    
    # Sökvägar att kontrollera
    search_patterns = [
        "/usr/share/core-odoo/addons/*/i18n/sv.po",
        "/usr/share/odoo-*/*/*/i18n/sv.po",
        "/usr/share/odooext-*/*/*/i18n/sv.po",
    ]
    
    for pattern in search_patterns:
        for po_file in glob.glob(pattern, recursive=True):
            try:
                with open(po_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                if len(lines) >= 3:
                    third_line = lines[2].strip()
                    module_name = extract_module_name(third_line)
                    
                    # Hämta modulnamn från sökväg
                    path_module = os.path.basename(os.path.dirname(os.path.dirname(po_file)))
                    
                    status = "OK" if module_name == path_module else "FEL"
                    results.append({
                        'file': po_file,
                        'path_module': path_module,
                        'third_line_module': module_name,
                        'third_line': third_line,
                        'status': status
                    })
            except Exception as e:
                results.append({
                    'file': po_file,
                    'error': str(e),
                    'status': 'KAN_INTE_LÄSAS'
                })
    
    return results

# Kör kontrollen
if __name__ == "__main__":
    print("Kontrollerar .po-filer...\n")
    results = check_po_files()
    
    # Sammanfattning
    errors = [r for r in results if r['status'] != 'OK']
    print(f"Totalt {len(results)} filer hittade")
    print(f"{len([r for r in results if r['status'] == 'OK'])} OK")
    print(f"{len(errors)} med fel\n")
    
    if errors:
        print("## FILER MED FEL:")
        for result in errors:
            print(f"\n{result['file']}")
            if 'error' in result:
                print(f"  FEL: {result['error']}")
            else:
                print(f"  Sökväg: {result['path_module']}")
                print(f"  Rad 3:  {result['third_line_module']}")
                print(f"  Status: {result['status']}")
