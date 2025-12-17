#!/usr/bin/python3
import argparse
import polib
import sys
from pathlib import Path

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
    parser.add_argument("-s", "--source", required=True,
                        help="Source file (original .po)")
    parser.add_argument("-t", "--target", required=True,
                        help="Target file (edited .po)")
    parser.add_argument("-o", "--output",
                        help="Output file (.po) with changes (default: stdout)")
    return parser.parse_args()

def main():
    args = parse_args()

    source_path = Path(args.source)
    target_path = Path(args.target)

    if not source_path.exists():
        raise SystemExit(f"Source file missing: {source_path}")
    if not target_path.exists():
        raise SystemExit(f"Target file missing: {target_path}")

    source_po = polib.pofile(str(source_path))
    target_po = polib.pofile(str(target_path))

    out_po = build_output_po(source_po, target_po)

    if args.output:
        output_path = Path(args.output)
        out_po.save(str(output_path))
        print(f"Wrote {len(out_po)} entries to {output_path}", file=sys.stderr)
    else:
        # Write PO content directly to stdout
        sys.stdout.write(str(out_po))
        print(f"\nWrote {len(out_po)} entries to stdout", file=sys.stderr)

if __name__ == "__main__":
    main()
