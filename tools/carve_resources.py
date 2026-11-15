#!/usr/bin/env python3
"""Carve embedded resource blobs out of a GraalVM native-image heap (.svm_hea).

Detects PNG/JPEG/TTF/OGG/WAV/OBJ/GLSL/JSON blobs by magic bytes, carves each
blob, and (best effort) associates it with the closest resource-path string in
the heap so files land under their original names.

Usage: python carve_resources.py <image> <heap_file_offset> <heap_size> <outdir>
"""
import mmap
import os
import struct
import sys
from pathlib import Path

PNG_SIG = b"\x89PNG\r\n\x1a\n"
JPEG_SIG = b"\xff\xd8\xff"
TTF_SIGS = (b"\x00\x01\x00\x00\x00", b"OTTO\x00")
OGG_SIG = b"OggS"
RIFF_SIG = b"RIFF"
WEBP = b"WEBP"

PATH_TOKENS = [b"assets/minecraft/client/"]
MIN_PATH = 12


def find_iend(data, start):
    idx = data.find(b"IEND", start)
    if idx < 0:
        return -1
    return idx + 8


def find_eoi(data, start):
    idx = data.find(b"\xff\xd9", start)
    if idx < 0:
        return -1
    return idx + 2


def carve_text(data, start, limit):
    """Printable-text blob: stop at first non-printable/control byte."""
    end = start
    max_end = min(start + limit, len(data))
    while end < max_end:
        c = data[end]
        if c < 0x09 or (0x0E <= c <= 0x1F) or c > 0x7E:
            break
        end += 1
    return end


def nearby_path(data, pos, radius=16384):
    lo = max(0, pos - radius)
    hi = min(len(data), pos + radius)
    window = data[lo:hi]
    best = None
    for tok in PATH_TOKENS:
        i = window.find(tok)
        if i >= 0:
            end = i
            while end < len(window) and window[end] not in (0,):
                end += 1
            cand = window[i:end]
            if len(cand) < 4096 and cand.count(b"/") >= 2:
                best = cand.decode("ascii", "replace")
                break
    return best


def safe_name(path, fallback_idx, ext):
    if path:
        name = path.replace("assets/minecraft/client/", "").replace("/", "_")
        if name and not name.startswith("_"):
            return name
    return f"unknown_{fallback_idx}.{ext}"


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 1
    image, heap_off, heap_size, outdir = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), sys.argv[4]
    Path(outdir).mkdir(parents=True, exist_ok=True)
    f = open(image, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    heap = mm[heap_off:heap_off + heap_size]
    report = []
    n = 0

    # PNG
    pos = 0
    while True:
        i = heap.find(PNG_SIG, pos)
        if i < 0:
            break
        end = find_iend(heap, i)
        if end > 0 and end - i > 60:
            blob = heap[i:end]
            name = nearby_path(heap, i)
            fn = safe_name(name, n, "png")
            (Path(outdir) / fn).write_bytes(blob)
            report.append(f"PNG  0x{heap_off + i:X} size={end - i} -> {fn} ({name})")
            n += 1
        pos = i + 8
        if n > 5000:
            break

    # JPEG
    pos = 0
    while True:
        i = heap.find(JPEG_SIG, pos)
        if i < 0:
            break
        if heap[i + 3] in (0xE0, 0xE1, 0xEE, 0xDB):
            end = find_eoi(heap, i)
            if end > 0 and end - i > 100:
                blob = heap[i:end]
                name = nearby_path(heap, i)
                fn = safe_name(name, n, "jpg")
                (Path(outdir) / fn).write_bytes(blob)
                report.append(f"JPEG 0x{heap_off + i:X} size={end - i} -> {fn} ({name})")
                n += 1
                pos = end
            else:
                pos = i + 3
        else:
            pos = i + 3
        if n > 5000:
            break

    # TTF
    pos = 0
    while True:
        found = False
        for sig in TTF_SIGS:
            i = heap.find(sig, pos)
            if i >= 0:
                end = i + 400_000
                end = min(end, len(heap))
                while end > i and heap[end - 1:end] == b"\x00":
                    end -= 1
                blob = heap[i:end]
                name = nearby_path(heap, i)
                if name and name.endswith(".ttf"):
                    fn = safe_name(name, n, "ttf")
                    (Path(outdir) / fn).write_bytes(blob)
                    report.append(f"TTF  0x{heap_off + i:X} size~{end - i} -> {fn} ({name})")
                    n += 1
                found = True
                pos = i + 5
                break
        if not found or n > 5000:
            break

    # OGG
    pos = 0
    while True:
        i = heap.find(OGG_SIG, pos)
        if i < 0:
            break
        end = heap.find(b"OggS", i + 4)
        if end < 0:
            end = i + 300_000
        blob = heap[i:min(end, i + 300_000)]
        name = nearby_path(heap, i)
        if name and (name.endswith(".ogg") or "sounds" in name):
            fn = safe_name(name, n, "ogg")
            (Path(outdir) / fn).write_bytes(blob)
            report.append(f"OGG  0x{heap_off + i:X} size~{len(blob)} -> {fn} ({name})")
            n += 1
            pos = min(end, i + 300_000)
        else:
            pos = i + 4
        if n > 5000:
            break

    # WAV (RIFF): exact size from header
    pos = 0
    while True:
        i = heap.find(RIFF_SIG, pos)
        if i < 0:
            break
        if heap[i + 8:i + 12] == b"WAVE":
            size = struct.unpack_from("<I", heap, i + 4)[0]
            if 44 <= size <= 5_000_000 and i + size <= len(heap):
                blob = heap[i:i + size]
                name = nearby_path(heap, i)
                fn = safe_name(name, n, "wav")
                (Path(outdir) / fn).write_bytes(blob)
                report.append(f"WAV  0x{heap_off + i:X} size={size} -> {fn} ({name})")
                n += 1
                pos = i + size
            else:
                pos = i + 4
        else:
            pos = i + 4
        if n > 5000:
            break

    # GLSL / JSON text blobs
    pos = 0
    text_started = 0
    while True:
        i = heap.find(b"#version", pos)
        if i < 0:
            break
        end = carve_text(heap, i, 40_000)
        blob = heap[i:end]
        if len(blob) > 60:
            is_frag = b"\nprecision" in blob or b"gl_FragColor" in blob or b" out vec4" in blob or b"fragColor" in blob
            ext = "frag" if is_frag else "vert"
            name = nearby_path(heap, i)
            fn = safe_name(name, n, ext)
            (Path(outdir) / fn).write_bytes(blob)
            report.append(f"GLSL 0x{heap_off + i:X} size={end - i} -> {fn} ({name})")
            n += 1
            pos = end
        else:
            pos = i + 8
        if n > 5000:
            break

    (Path(outdir) / "_carve_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"carved {n} files; report in _carve_report.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
