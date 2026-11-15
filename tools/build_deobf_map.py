#!/usr/bin/env python3
"""Build the obfuscated -> MCP class deobfuscation map.

Joins the jar entry names recovered from the native image's embedded signed
manifest (data/JAR_ENTRIES.txt) against the official MCP 9.19 SRG mappings for
1.8.9 (joined.srg; md5 f5f8e81cd42f831d8d9979c0ffcb194e).

Output: data/DEOBF_CLASS_MAP.csv with columns obf_name,srg_name,source
where source = mcp (mapped) | unnamed (not in mappings) | netty (library).

Usage: python build_deobf_map.py <joined.srg> <jar_entries.txt> <out.csv>
"""
import csv
import sys


def main():
    srg_path, entries_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    srg = {}
    with open(srg_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("CL: "):
                parts = line[4:].split()
                if len(parts) == 2:
                    obf, srgname = parts
                    srg[obf.replace(".class", "")] = srgname

    rows = []
    unnamed = 0
    with open(entries_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("Name: "):
                continue
            obf = line[6:].replace(".class", "")
            if obf in srg:
                rows.append((obf, srg[obf], "mcp"))
            elif "/" in obf or "." in obf:
                rows.append((obf, obf, "library"))
            else:
                rows.append((obf, "", "unnamed"))
                unnamed += 1

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["obf_name", "srg_name", "source"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows ({unnamed} unnamed) -> {out_path}")


if __name__ == "__main__":
    main()
