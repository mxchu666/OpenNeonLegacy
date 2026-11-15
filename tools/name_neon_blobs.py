#!/usr/bin/env python3
"""Assign resource-path names to the unknown (Neon-specific) carved blobs.

Consumes the outputs of the background analysis pass:
  - unknown_blobs.json  [{ext, heap_rel, size}]  blobs whose content hash is not
                        in the vanilla 1.8.9 client.jar (i.e. Neon assets)
  - path_cluster.json   [[path, heap_rel]]       unique resource-path strings

Naming rule: nearest path by heap position, extension must match, radius cap
(8 MB) because SVM registers resources in allocation order. Unmatched blobs are
written with a placeholder name including their heap offset.

Usage: python name_neon_blobs.py <image> <heap_off> <unknown_blobs.json> <path_cluster.json> <outdir>
"""
import json
import mmap
import struct
import sys
from pathlib import Path

PNG_SIG = b"\x89PNG\r\n\x1a\n"
IHDR_OK = b"\x00\x00\x00\x0dIHDR"
JPG_END = b"\xff\xd9"
TTF_SIG = b"\x00\x01\x00\x00"
OTF_SIG = b"OTTO"
OGG_SIG = b"OggS"
RIFF_SIG = b"RIFF"

RADIUS = 8 << 20

TXT_EXTS = {"json", "frag", "vert", "glsl", "obj", "md", "txt", "dnet",
            "mtl", "properties", "lang", "metadata"}


def ext_of(path):
    e = path.rsplit(".", 1)[-1].lower()
    return e


def revalidate(heap, ext, s, size):
    """Carve with format-exact bounds again (paths carry the true length)."""
    if ext == "png":
        if heap[s:s + 16] != PNG_SIG or heap[s + 8:s + 16] != IHDR_OK:
            return None
        e = heap.find(b"IEND", s)
        if e < 0:
            return None
        return e + 8
    if ext == "jpg":
        e = heap.find(JPG_END, s)
        if e < 0:
            return None
        return e + 2
    if ext == "ttf":
        nt = struct.unpack_from(">H", heap, s + 4)[0]
        if not (0 < nt <= 100):
            return None
        max_end = s + 12 + 16 * nt
        for t in range(nt):
            off = s + 12 + 16 * t
            to, tl = struct.unpack_from(">II", heap, off + 8)
            max_end = max(max_end, to + ((tl + 3) & ~3))
        return max_end
    if ext == "ogg":
        end = s
        limit = s + (8 << 20)
        while end < limit:
            nxt = heap.find(OGG_SIG, end + 4)
            if nxt < 0 or nxt > limit or nxt - end > (1 << 20):
                break
            end = nxt
        return min(end + 27 + 255, limit) if end > s else None
    if ext == "wav":
        if heap[s + 8:s + 12] != b"WAVE":
            return None
        n = struct.unpack_from("<I", heap, s + 4)[0]
        return s + n if 44 <= n <= (8 << 20) and s + n <= len(heap) else None
    if ext == "txt":
        end = s
        limit = min(s + 1_500_000, len(heap))
        while end < limit:
            c = heap[end]
            if c < 0x09 or (0x0E <= c <= 0x1F) or c > 0x7E:
                break
            end += 1
        return end if end - s > 20 else None
    return None


def main():
    image, heap_off, ub_path, pc_path, outdir = (
        sys.argv[1], int(sys.argv[2], 0), sys.argv[3], sys.argv[4], sys.argv[5])
    Path(outdir).mkdir(parents=True, exist_ok=True)
    f = open(image, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    heap = mm[heap_off:heap_off + 0x18823000]

    unknown = json.load(open(ub_path, encoding="utf-8"))
    paths = json.load(open(pc_path, encoding="utf-8"))
    # neon-only paths keep the mapping clean (vanilla paths already used by hash)
    neon_paths = [(int(o, 16), p) for p, o in paths if "/client/" in p or p.startswith("assets/minecraft/client")]
    neon_paths.sort()
    print(f"unknown blobs: {len(unknown)}  neon paths: {len(neon_paths)}")

    assigned, failed = [], []
    used_paths = set()
    import bisect
    pp = [p[0] for p in neon_paths]

    for b in unknown:
        ext, s, size = b["ext"], int(b["heap_rel"], 16), b["size"]
        # candidate paths within radius
        k = bisect.bisect_left(pp, s)
        cands = []
        for kk in range(max(0, k - 4), min(len(neon_paths), k + 5)):
            o, pth = neon_paths[kk]
            d = abs(o - s)
            if d <= RADIUS and pth not in used_paths:
                cands.append((d, pth))
        cands.sort()
        chosen = None
        for d, pth in cands:
            pe = ext_of(pth)
            ok = (pe == ext) or (ext == "txt" and pe in TXT_EXTS) or \
                 (pe == "jpeg" and ext == "jpg") or (pe == "ttf" and ext == "ttf")
            if ok:
                chosen = pth
                break
        if chosen is None:
            failed.append({"ext": ext, "heap_rel": hex(s), "size": size})
            continue
        used_paths.add(chosen)
        e = revalidate(heap, ext, s, size)
        if e is None:
            failed.append({"ext": ext, "heap_rel": hex(s), "size": size, "path": chosen,
                           "note": "revalidation failed"})
            continue
        rel = chosen.replace("assets/", "")
        out = Path(outdir) / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(heap[s:e])
        assigned.append({"path": chosen, "ext": ext, "size": e - s,
                         "heap_rel": hex(s)})

    report = {"assigned": assigned, "failed": failed}
    (Path(outdir) / "_neon_named_report.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8")
    print(f"assigned={len(assigned)} failed={len(failed)}")
    for a in assigned:
        print(f"  {a['path']}  ({a['size']} B @ {a['heap_rel']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
