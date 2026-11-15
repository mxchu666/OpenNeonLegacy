#!/usr/bin/env python3
"""Targeted carve of Neon Legacy's own assets (paths listed in NEON_ASSETS.txt)
from the GraalVM native-image heap.

For each known asset path:
  1. find every occurrence of the path string in the heap,
  2. scan +-MAX_RADIUS around each occurrence for the file's magic signature,
  3. validate and carve with format-exact bounds (PNG/JPEG/WAV exact, others heuristic),
  4. write under the original relative name.

Usage: python carve_neon_assets.py <image> <heap_file_offset> <heap_size> <assets_list> <outdir>
"""
import json
import mmap
import os
import struct
import sys
from pathlib import Path

PNG_SIG = b"\x89PNG\r\n\x1a\n"
IHDR_OK = b"\x00\x00\x00\x0dIHDR"
JPEG_SIG = b"\xff\xd8\xff"
TTF_SIG = b"\x00\x01\x00\x00"
OGG_SIG = b"OggS"
RIFF_SIG = b"RIFF"

MAX_RADIUS = 1 << 18  # 256 KiB around each path occurrence


def carve_png(heap, i):
    if heap[i + 8:i + 16] != IHDR_OK:
        return None
    end = heap.find(b"IEND", i)
    if end < 0:
        return None
    end += 8
    if end - i > (16 << 20):
        return None
    return i, end


def carve_jpg(heap, i):
    end = heap.find(b"\xff\xd9", i)
    if end < 0 or end - i > (8 << 20) or end - i < 100:
        return None
    return i, end + 2


def carve_ttf(heap, i):
    # sfnt: version at 0, numTables at +4; estimate size via table directory
    try:
        num_tables = struct.unpack_from(">H", heap, i + 4)[0]
        if num_tables == 0 or num_tables > 100:
            return None
        max_end = i + 12 + 16 * num_tables
        for t in range(num_tables):
            off = i + 12 + 16 * t
            tbl_off, tbl_len = struct.unpack_from(">II", heap, off + 8)
            end = tbl_off + ((tbl_len + 3) & ~3)
            if end > max_end:
                max_end = end
            if max_end - i > (4 << 20):
                return None
        return i, max_end
    except Exception:
        return None


def carve_ogg(heap, i):
    # consecutive OggS pages until a gap without one
    end = i
    limit = i + (4 << 20)
    while end < limit:
        nxt = heap.find(OGG_SIG, end + 4)
        if nxt < 0 or nxt > limit:
            break
        if nxt - end > (1 << 20):
            break
        end = nxt
    if end == i:
        return None
    return i, min(end + 27 + 255, limit)


def carve_wav(heap, i):
    if heap[i + 8:i + 12] != b"WAVE":
        return None
    size = struct.unpack_from("<I", heap, i + 4)[0]
    if not (44 <= size <= (8 << 20)) or i + size > len(heap):
        return None
    return i, i + size


def carve_text(heap, i, start_anchor):
    end = i
    limit = min(i + 120_000, len(heap))
    while end < limit:
        c = heap[end]
        if c < 0x09 or (0x0E <= c <= 0x1F) or c > 0x7E:
            break
        end += 1
    if end - i < 40:
        return None
    return i, end


def ext_for(path):
    e = path.rsplit(".", 1)[-1].lower()
    return e if e in ("png", "jpg", "jpeg", "ttf", "ogg", "wav", "obj", "json", "frag", "vert", "glsl", "dnet", "md") else None


def sigs_for(ext):
    if ext == "png":
        return [PNG_SIG]
    if ext in ("jpg", "jpeg"):
        return [JPEG_SIG]
    if ext == "ttf":
        return [TTF_SIG]
    if ext == "ogg":
        return [OGG_SIG]
    if ext == "wav":
        return [RIFF_SIG]
    if ext == "obj":
        return [b"v ", b"#", b"o ", b"mtllib"]
    if ext == "json":
        return [b"{", b"["]
    if ext in ("frag", "vert", "glsl"):
        return [b"#version", b"precision", b"uniform", b"/*"]
    return []


def carve_for(heap, pos, ext):
    for sig in sigs_for(ext):
        start = pos
        while True:
            j = heap.find(sig, start)
            if j < 0 or j - pos > MAX_RADIUS:
                break
            if j - pos > -MAX_RADIUS:
                if ext == "png":
                    r = carve_png(heap, j)
                elif ext in ("jpg", "jpeg"):
                    r = carve_jpg(heap, j)
                elif ext == "ttf":
                    r = carve_ttf(heap, j)
                elif ext == "ogg":
                    r = carve_ogg(heap, j)
                elif ext == "wav":
                    r = carve_wav(heap, j)
                else:
                    r = carve_text(heap, j, sig)
                if r:
                    return r
            start = j + max(1, len(sig))
    return None


def main():
    image, heap_off, heap_size, assets_list, outdir = (
        sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), sys.argv[4], sys.argv[5])
    Path(outdir).mkdir(parents=True, exist_ok=True)
    f = open(image, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    heap = mm[heap_off:heap_off + heap_size]

    paths = [l.strip() for l in open(assets_list, encoding="utf-8") if l.strip()]
    found, missing = [], []
    for p in paths:
        ext = ext_for(p)
        if ext is None:
            missing.append((p, "unknown extension"))
            continue
        rel = p.replace("assets/minecraft/client/", "")
        out = Path(outdir) / rel
        best = None
        pos = 0
        occurrences = 0
        while True:
            i = heap.find(p.encode(), pos)
            if i < 0:
                break
            occurrences += 1
            r = carve_for(heap, i, ext)
            if r and (best is None or (r[1] - r[0]) < (best[1] - best[0])):
                best = r
            pos = i + len(p)
            if occurrences > 64:
                break
        if best:
            blob = heap[best[0]:best[1]]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(blob)
            found.append((p, len(blob), heap_off + best[0]))
        else:
            missing.append((p, f"no valid blob near {occurrences} occurrences"))

    (Path(outdir) / "_carve_report.json").write_text(
        json.dumps({"found": [{"path": p, "size": s, "heap_offset": hex(o)} for p, s, o in found],
                    "missing": [{"path": p, "reason": r} for p, r in missing]}, indent=1),
        encoding="utf-8")
    print(f"found={len(found)} missing={len(missing)}")
    for p, r in missing[:20]:
        print("MISS:", p, "--", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
