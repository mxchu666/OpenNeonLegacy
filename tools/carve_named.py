#!/usr/bin/env python3
"""Carve resource blobs from the native-image heap and name them exactly.

Every blob is carved with format-exact bounds and validated with the SVM byte[]
header (int32 length at data_start-4). Naming is exact for blobs whose size
matches a vanilla 1.8.9 client.jar resource (same original bytes). Leftover
blobs (Neon-specific assets) get the nearest resource-path string found in the
heap as their name, else a placeholder name.

Usage: python carve_named.py <image> <heap_off> <heap_size> <vanilla_jar> <outdir>
"""
import json
import mmap
import struct
import sys
import zipfile
from pathlib import Path

PNG_SIG = b"\x89PNG\r\n\x1a\n"
IHDR_OK = b"\x00\x00\x00\x0dIHDR"
JPEG_SIG = b"\xff\xd8\xff"
TTF_SIG = b"\x00\x01\x00\x00"
OTF_SIG = b"OTTO"
OGG_SIG = b"OggS"
RIFF_SIG = b"RIFF"


def end_png(heap, i):
    if heap[i + 8:i + 16] != IHDR_OK:
        return None
    e = heap.find(b"IEND", i)
    if e < 0 or e + 8 - i > (32 << 20):
        return None
    return e + 8


def end_jpg(heap, i):
    e = heap.find(b"\xff\xd9", i)
    if e < 0 or e - i > (16 << 20) or e - i < 100:
        return None
    return e + 2


def end_ttf(heap, i):
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
            if max_end - i > (6 << 20):
                return None
        return max_end
    except Exception:
        return None


def end_ogg(heap, i):
    end = i
    limit = i + (8 << 20)
    while end < limit:
        nxt = heap.find(OGG_SIG, end + 4)
        if nxt < 0 or nxt > limit or nxt - end > (1 << 20):
            break
        end = nxt
    return min(end + 27 + 255, limit) if end > i else None


def end_wav(heap, i):
    if heap[i + 8:i + 12] != b"WAVE":
        return None
    size = struct.unpack_from("<I", heap, i + 4)[0]
    if not (44 <= size <= (8 << 20)) or i + size > len(heap):
        return None
    return i + size


def end_text(heap, i):
    end = i
    limit = min(i + 1_500_000, len(heap))
    while end < limit:
        c = heap[end]
        if c < 0x09 or (0x0E <= c <= 0x1F) or c > 0x7E:
            break
        end += 1
    return end if end - i > 20 else None


RUNS = [
    ("png", PNG_SIG, end_png),
    ("jpg", JPEG_SIG, end_jpg),
    ("ttf", TTF_SIG, end_ttf),
    ("ttf", OTF_SIG, end_ttf),
    ("ogg", OGG_SIG, end_ogg),
    ("wav", RIFF_SIG, end_wav),
]

TEXT_ANCHORS = (b"#version", b"precision mediump", b"uniform float")


def main():
    image, heap_off, heap_size, vanilla_jar, outdir = (
        sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), sys.argv[4], sys.argv[5])
    Path(outdir).mkdir(parents=True, exist_ok=True)
    f = open(image, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    heap = mm[heap_off:heap_off + heap_size]

    # vanilla resource sizes
    # vanilla resource hashes
    import hashlib
    hash2names = {}
    with zipfile.ZipFile(vanilla_jar) as z:
        for info in z.infolist():
            if info.file_size > 0 and not info.filename.startswith("META-INF") and "." in info.filename \
                    and not info.filename.endswith(".class"):
                h = hashlib.sha1(z.read(info.filename)).hexdigest()
                hash2names.setdefault(h, []).append(info.filename)

    blobs = []
    for ext, sig, ender in RUNS:
        pos = 0
        while True:
            i = heap.find(sig, pos)
            if i < 0:
                break
            e = ender(heap, i)
            if e is None:
                pos = i + len(sig)
                continue
            size = e - i
            if i >= 4 and struct.unpack_from("<i", heap, i - 4)[0] == size:
                blobs.append([ext, i, e])
                pos = e
            else:
                pos = i + len(sig)
    for anchor in TEXT_ANCHORS:
        pos = 0
        while True:
            i = heap.find(anchor, pos)
            if i < 0:
                break
            e = end_text(heap, i)
            if e is None:
                pos = i + len(anchor)
                continue
            size = e - i
            if i >= 4 and struct.unpack_from("<i", heap, i - 4)[0] == size:
                blobs.append(["txt", i, e])
                pos = e
            else:
                pos = i + len(anchor)
    blobs.sort(key=lambda b: b[1])

    # path strings in heap (all occurrences)
    path_pos = []  # (pos, path)
    pos = 0
    needle = b"assets/"
    while True:
        i = heap.find(needle, pos)
        if i < 0:
            break
        end = i
        limit = min(i + 4096, len(heap))
        while end < limit and 0x20 <= heap[end] <= 0x7E:
            end += 1
        s = heap[i:end].decode("ascii", "replace")
        if s.count("/") >= 2 and "." in s.rsplit("/", 1)[-1]:
            path_pos.append((i, s))
        pos = i + 1

    import bisect
    path_positions = [p[0] for p in path_pos]

    def nearest_path(i):
        if not path_pos:
            return None
        k = bisect.bisect_left(path_positions, i)
        best = None
        for kk in (k - 1, k, k + 1):
            if 0 <= kk < len(path_pos):
                d = abs(path_pos[kk][0] - i)
                if best is None or d < best[0]:
                    best = (d, path_pos[kk][1])
        return best[1] if best else None

    used = set()
    assigned, leftovers = [], []
    for ext, s, e in blobs:
        size = e - s
        sha = hashlib.sha1(heap[s:e]).hexdigest()
        cands = [n for n in hash2names.get(sha, []) if n not in used]
        name = None
        src = None
        if len(cands) == 1:
            name = cands[0]
            src = "vanilla-hash"
        elif cands:
            np = nearest_path(s)
            if np and np in cands:
                name = np
            else:
                name = cands[0]
            src = "vanilla-hash+hint"
        else:
            np = nearest_path(s)
            if np and ("." + ext in np or (ext == "txt" and np.rsplit(".", 1)[-1].lower() in
                                           ("json", "frag", "vert", "glsl", "obj", "md", "txt", "dnet", "lang", "properties"))):
                name = np
                src = "nearest-path"
        if name:
            used.add(name)
            rel = name.strip().rstrip('",;)]}')
            out = Path(outdir) / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(heap[s:e])
            assigned.append({"path": name, "ext": ext, "size": size, "heap_offset": hex(heap_off + s), "matched_by": src})
        else:
            leftovers.append({"ext": ext, "size": size, "heap_offset": hex(heap_off + s)})
            (Path(outdir) / f"_leftover_{ext}_{hex(heap_off + s)[2:]}.{ext}").write_bytes(heap[s:e])

    report = {"assigned_count": len(assigned), "leftover_count": len(leftovers), "assigned": assigned, "leftovers": leftovers}
    (Path(outdir) / "_named_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"blobs={len(blobs)} assigned={len(assigned)} leftovers={len(leftovers)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
