#!/usr/bin/env python3
"""Generate deobfuscated Java skeleton files for every class in the signed
manifest embedded in the GraalVM image heap.

This is NOT decompilation and does not pretend to be: the original bytecode
was destroyed by the AOT compilation (no .class exists anywhere in the
artifact — verified, see docs/OBFUSCATION.md). Each skeleton restores the
real package/class name via the MCP 9.19 rename map (data/DEOBF_CLASS_MAP.csv)
so the AOT reverse-engineering work has a navigable tree. Inner classes from
the manifest are listed in their parent's file, not as separate files.

Usage: python dump_class_skeletons.py <repo_root>
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

HEADER = """\
/*
 * Esqueleto estructural — OpenNeonLegacy (NO es descompilación).
 *
 * El bytecode original fue destruido por la compilación AOT de GraalVM: no
 * existe ningún .class ni .java original en el artefacto (verificado, ver
 * docs/OBFUSCATION.md). Este archivo solo restaura el nombre real de la
 * clase vía MCP 9.19 (data/DEOBF_CLASS_MAP.csv) para que el trabajo AOT
 * tenga un árbol navegable.
 *
 * Clase obfuscada original: {obf}
 * Cuerpos de métodos: reconstrucción manual desde el AOT x86-64 de
 * extracted/neon.exe — guía en decompiled/README.md.
 */
package {package};

public class {cls} {{
{body}}}
"""


def main(repo):
    data = Path(repo) / "data"
    out_root = Path(repo) / "decompiled" / "java-skeletons"

    m = {}
    with open(data / "DEOBF_CLASS_MAP.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m[row["obf_name"]] = row["srg_name"]

    classes, inners = [], defaultdict(list)
    for line in open(data / "JAR_ENTRIES.txt", encoding="utf-8"):
        line = line.strip()
        if line.startswith("Name: ") and line.endswith(".class"):
            c = line[6:-6]
            if "$" in c:
                inners[c.split("$", 1)[0]].append(c)
            else:
                classes.append(c)

    top = sorted(set(classes))
    unmapped = [c for c in top if c not in m]
    if unmapped:
        raise SystemExit(f"clases sin mapping MCP: {unmapped[:5]}… ({len(unmapped)})")

    out_root.mkdir(parents=True, exist_ok=True)
    seen_paths = {}
    for obf in top:
        srg = m[obf]  # net/minecraft/util/EnumChatFormatting
        pkg, _, cls = srg.rpartition("/")
        d = out_root / pkg
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{cls}.java"
        if path in seen_paths:
            raise SystemExit(f"colisión {path}: {seen_paths[path]} vs {obf}")
        seen_paths[path] = obf
        inner_note = ""
        if obf in inners:
            lst = "".join(f"    //   {i}\n" for i in sorted(inners[obf]))
            inner_note = f"    // Inner classes en el manifest original:\n{lst}"
        path.write_text(HEADER.format(obf=obf, package=pkg.replace("/", "."),
                                      cls=cls, body=inner_note), encoding="utf-8", newline="\n")

    # índice por paquete
    by_pkg = defaultdict(list)
    for obf in top:
        pkg, _, cls = m[obf].rpartition("/")
        by_pkg[pkg].append((obf, cls))
    lines = ["# Índice de esqueletos — clases del manifest firmado\n",
             f"{len(top)} clases top-level + {sum(len(v) for v in inners.values())} inner = "
             f"{len(top) + sum(len(v) for v in inners.values())} entradas del manifest.\n",
             "Nombre real vía MCP 9.19. Esqueletos en `java-skeletons/`.\n"]
    for pkg in sorted(by_pkg):
        lines.append(f"\n## {pkg or '(default)'} — {len(by_pkg[pkg])} clases\n")
        lines.append("| obf | clase |")
        lines.append("|---|---|")
        for obf, cls in sorted(by_pkg[pkg], key=lambda x: x[1]):
            lines.append(f"| {obf} | {cls} |")
    (out_root / "_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"top={len(top)} inner={sum(len(v) for v in inners.values())} "
          f"packages={len(by_pkg)} -> {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
