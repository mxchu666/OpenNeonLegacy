#!/usr/bin/env python3
"""Final verified carve of Neon Legacy's own assets from the GraalVM image heap.

Every offset below was fixed by a content probe, not by path proximity:
  - PNGs: exact blob bounds verified against the heap PNG inventory,
    identity by visual inspection (zoom sheets) or exact-dims font pairing.
  - JPEG/OGG/DNET: SVM byte[] header (int32 length at data_start-4) verified.
  - OBJ: geometry stats (v/f counts) must match the known Utah teapot numbers.
  - Shaders: len-prefix verified + #version anchor + GLSL keyword match.
  - Font metas: JSON must parse; atlas dims must equal meta dims.

Anonymous font pairs are shipped as font_<width>/ on purpose: no probe can
recover the real folder name (see docs/RECOVERY_LIMITS.md).

Usage: python carve_final.py <neon.exe> <repo_root>
"""
import hashlib
import json
import mmap
import struct
import sys
from pathlib import Path

HEAP_FILE_OFF = 0x77D7000
HEAP_SIZE = 0x18823000
CLIENT = "assets/minecraft/client/"
PNG_SIG = b"\x89PNG\r\n\x1a\n"


def add(out, kind, off, size, conf, method, note="", expect=None):
    A.append(dict(out=out, kind=kind, off=off, size=size, conf=conf,
                  method=method, note=note, expect=expect or {}))


A = []

# ---- icons (visual zoom sheets) ----
add("icons/neon_16.png", "png", 0x33980d0, None, "high", "visual-zoom", "triangulo neon 16x16 (branding)")
add("icons/neon_32.png", "png", 0x32f20f8, None, "high", "visual-zoom", "triangulo neon 32x32 (branding)")
add("icons/stitch_16.png", "png", 0x34141b0, None, "medium", "visual-zoom", "icono stitch 16x16")
add("icons/stitch_32.png", "png", 0x31754d8, None, "high", "visual-zoom", "icono stitch 32x32")
add("icons/jeffbenzos32.png", "png", 0x32a82c0, None, "medium", "visual-zoom", "pinguino con cadena; asignado por eliminacion (jeffbenzos16 no embebido)")
# ---- esp ----
add("esp/cop.png", "png", 0x101038, None, "high", "visual-zoom", "mugshot estilo policia 299x333")
add("esp/floyd.png", "png", 0x128f3f78, None, "medium", "visual-zoom", "retrato 252x476 (estilo Floyd)")
# ---- images ----
add("images/Sayori_Hanging_s_kill.png", "png", 0x138e6720, None, "high", "visual-zoom", "imagen DDLC referencial 286x1050")
add("images/background_noise.png", "png", 0xcdf8850, None, "medium", "visual-zoom", "ruido marron-nube 1024x1024 (fondo blur)")
add("images/cross.png", "png", 0x1c2f758, None, "high", "visual-zoom", "X blanca 280x280 (cursor de aim/esp)")
add("images/esp_noise.png", "png", 0x1758c38, None, "medium", "visual-zoom", "ruido ESP; twin no-carvado en 0x175ffc8")
add("images/freaky.png", "png", 0xa15d2e0, None, "medium", "visual-zoom", "palomas con dientes (meme)")
add("images/glass_noise.png", "png", 0x1101038, None, "medium", "visual-zoom", "ruido granular 256x256 (shader glass)")
add("images/loading.png", "png", 0x290eae0, None, "high", "visual-zoom", "pantalla 'Loading' 800x600")
add("images/logo.png", "png", 0x1e0b988, None, "medium", "visual-zoom", "triangulo neon 223x193 (logo grande)")
add("images/no_image.png", "png", 0x32210c8, None, "high", "visual-zoom", "checkerboard magenta 1920x1080 (placeholder)")
add("images/run.png", "png", 0x2768118, None, "medium", "visual-zoom", "circulo play rojo (boton)")
add("images/snowflake.png", "png", 0x1582188, None, "high", "visual-zoom", "copo 200x200 (shader snow/stars ESP)")
add("images/stitch.png", "png", 0xcf9ab88, None, "high", "visual-zoom", "stitch 908x954 (artwork)")
add("images/unknown.png", "png", 0x31dbda0, None, "medium", "visual-zoom", "checkerboard magenta (variante)")
add("images/icons/close.png", "png", 0x313ca30, None, "medium", "visual-zoom", "X roja 38x38 (boton cerrar)")
add("images/icons/cursor.png", "png", 0x3593710, None, "high", "visual-zoom", "cursor 12x19")
add("images/icons/thonk.png", "png", 0x797928, None, "high", "visual-zoom", "thonk 640x640 (emoji GUI)")
add("images/portraits/steve.png", "png", 0x2770140, None, "high", "visual-zoom", "retrato steve 128x128")
add("images/background.jpeg", "raw_len", 0xa1c1b88, 249639, "high", "jpeg-unique", "unico JPEG grande no-vanilla del heap (fondo)")
add("orialeng.jpg", "raw_len", 0x1677078, 31638, "medium", "jpeg-unique", "JPEG no-vanilla; nombre por path string del heap")
# ---- fonts: blocky bitmap + 10 pares + 5 atlas-only ----
add("fonts/blocky.png", "png", 0x34a3568, None, "medium", "visual-zoom", "bitmap de font estilo MC 128x128")
for w, atlas in [(600, 0xbdeec58), (640, 0xd0068d0), (812, 0x11828640), (836, 0x132e8c30),
                 (884, 0x12930130), (1068, 0x11536c90), (1304, 0x96283e0), (1580, 0x12d8b658),
                 (2248, 0x08f82650), (2616, 0x1467b530)]:
    add(f"fonts/font_{w}/glyphmap.png", "png", atlas, None, "high", "dims-exact-pairing",
        "atlas MTSDF emparejado por dims exactas con metadata.json del mismo dir")
for w in (2224, 2228, 1056, 1088, 1292):
    atlas = {2224: 0x0f4139d0, 2228: 0xd336098, 1056: 0x1132ede0, 1088: 0xa1feaf8, 1292: 0x1161bcb8}[w]
    add(f"fonts/font_{w}/glyphmap.png", "png", atlas, None, "high", "dims-exact",
        "solo atlas: su metadata.json esta truncada en el heap (cola de GC); ver RECOVERY_LIMITS",
        expect={"w": w, "h": w})
# ---- shaders (keyword match, conf medium) ----
add("shader_v3/esp/snow.frag", "shader", 0x033a6c48, 1377, "medium", "keyword-glsl", "kw 'snow' + convencion uniforms MC")
add("shader_v3/esp/stars.frag", "shader", 0x0321d820, 2406, "medium", "keyword-glsl",
    "escogida sobre twin 0x03215bf8 (2449 B): esta usa uniforms MC (u_Sampler0/u_MaskSampler0); el twin es el raw glslsandbox")
add("shaders/jump_flood.frag", "shader", 0x030e3538, 3380, "medium", "keyword-glsl", "kw 'jfa' (jump flood outline)")
add("shader_v3/stencil.frag", "shader", 0x03289b90, 2105, "medium", "keyword-glsl", "kw 'stencil'")
add("shader_v3/model.frag", "shader", 0x033ece80, 1115, "medium", "keyword-glsl", "escogida sobre twin 0x034b3c38 (812 B): mayor tamano/keywords")
add("shader_v3/model.vert", "shader", 0x0344e190, 847, "medium", "keyword-glsl", "vert con u_mvp; solo esta asignada")
# ---- recursos ----
add("sounds/vine_boom.ogg", "raw_len", 0x205df78, 18822, "medium", "spectral-0.9925",
    "vine boom 3.265 s mono; sha canonico codingale 5d3b2731.. no matchea exacto en heap; twins 0x1784130/0x178b470 documentados")
add("subway/atlas.png", "png", 0x15609258, None, "medium", "visual-zoom",
    "collage 4500x5000 con tiles 'Subway Surfers'; su metadata.json esta corrupta en heap (ver RECOVERY_LIMITS)",
    expect={"w": 4500, "h": 5000})
add("classifier/hotdog.dnet", "raw_len", 0x14f153c0, 5311137, "high", "unique-format",
    "red neuronal Deep Netts (clasificador hotdog); unico blob dnet del heap")
add("models/teapot.obj", "obj", 0x7192366, 210584, "confirmed", "obj-stats",
    "Utah teapot NVIDIA exacta: 3643 verts, 6320 caras")


def ihdr_dims(heap, i):
    w, h = struct.unpack_from(">II", heap, i + 16)
    return w, h


def carve_png(heap, i, expect=None):
    if heap[i:i + 8] != PNG_SIG:
        raise ValueError(f"no PNG sig at {hex(i)}")
    end = heap.find(b"IEND", i, i + (20 << 20))
    if end < 0:
        raise ValueError(f"no IEND from {hex(i)}")
    end += 8
    w, h = ihdr_dims(heap, i)
    if expect:
        if (w, h) != (expect["w"], expect["h"]):
            raise ValueError(f"dims {w}x{h} != esperado {expect['w']}x{expect['h']} en {hex(i)}")
    return heap[i:end], w, h, end - i


def carve_raw_len(heap, i, size, sig=None):
    if i < 4 or struct.unpack_from("<i", heap, i - 4)[0] != size:
        got = struct.unpack_from("<i", heap, i - 4)[0] if i >= 4 else None
        raise ValueError(f"len-prefix {got} != {size} en {hex(i - 4)}")
    blob = heap[i:i + size]
    if sig and blob[:len(sig)] != sig:
        raise ValueError(f"sig {sig} no encontrada en {hex(i)}")
    return blob


def carve_shader(heap, i, size):
    got = struct.unpack_from("<i", heap, i - 4)[0] if i >= 4 else None
    if got != size:
        raise ValueError(f"shader len-prefix {got} != {size} en {hex(i - 4)}")
    blob = heap[i:i + size]
    if not blob.startswith(b"#version"):
        raise ValueError(f"shader sin #version en {hex(i)}")
    return blob


def carve_obj(heap, i, size):
    blob = heap[i:i + size]
    lines = blob.splitlines()
    v = sum(1 for l in lines if l.startswith(b"v "))
    f = sum(1 for l in lines if l.startswith(b"f "))
    if (v, f) != (3643, 6320):
        raise ValueError(f"teapot stats v={v} f={f} != (3643, 6320)")
    return blob


def main():
    image, repo = sys.argv[1], Path(sys.argv[2])
    f = open(image, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    heap = mm[HEAP_FILE_OFF:HEAP_FILE_OFF + HEAP_SIZE]
    if len(heap) != HEAP_SIZE:
        raise ValueError("heap slice incompleto")

    out_root = repo / CLIENT
    report, png_checks = [], []

    for e in A:
        off, kind = e["off"], e["kind"]
        if kind == "png":
            blob, w, h, size = carve_png(heap, off, e["expect"])
            png_checks.append((w, h, e["out"]))
        elif kind == "raw_len":
            sig = {".ogg": b"OggS", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff"}.get(
                e["out"].rsplit(".", 1)[-1].lower())
            blob = carve_raw_len(heap, off, e["size"], sig)
            size, w, h = e["size"], None, None
        elif kind == "shader":
            blob = carve_shader(heap, off, e["size"])
            size, w, h = e["size"], None, None
        elif kind == "obj":
            blob = carve_obj(heap, off, e["size"])
            size, w, h = e["size"], None, None
        else:
            raise ValueError(kind)

        out = out_root / e["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        report.append({
            "path": CLIENT + e["out"], "heap_offset": hex(HEAP_FILE_OFF + off),
            "heap_offset_rel": hex(off), "size": size,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "confidence": e["conf"], "method": e["method"], "note": e["note"],
            **({"png_dims": [w, h]} if w else {}),
        })

    # ---- font metadata.json: carve + parse + pair con su atlas ----
    # (off, len, width, lineHeight) — parseados del heap por tools/parse_fonts
    METAS = [
        (16988248, 51090, 600, 1.11328125), (9270480, 95642, 640, 1.272),
        (310535576, 842135, 812, 1.2001953125), (337265192, 630597, 836, 1.2),
        (168602968, 599363, 884, 1.2255859375), (128917280, 135314, 1068, 1.3935546875),
        (233395496, 187740, 1304, 1.171875), (214552888, 309526, 1580, 1.193359375),
        (199449952, 406525, 2248, 1.0), (289882664, 797212, 2616, 1.20703125),
    ]
    for off, size, w, line_h in METAS:
        if heap[off:off + 1] != b"{":
            raise ValueError(f"meta {w} sin '{{' en {hex(off)}")
        blob = heap[off:off + size]
        j = json.loads(blob.decode("utf-8", "strict"))
        if j["atlas"]["width"] != w or j["atlas"]["height"] != w:
            raise ValueError(f"meta {w} dims discrepantes")
        if abs(j["metrics"]["lineHeight"] - line_h) > 1e-9:
            raise ValueError(f"meta {w} lineHeight discrepante")
        rel = f"fonts/font_{w}/metadata.json"
        (out_root / rel).write_bytes(blob)
        report.append({
            "path": CLIENT + rel, "heap_offset": hex(HEAP_FILE_OFF + off),
            "heap_offset_rel": hex(off), "size": size,
            "sha256": hashlib.sha256(blob).hexdigest(), "confidence": "high",
            "method": "meta-parse", "note": "metadata MTSDF parseada y emparejada por dims con su glyphmap",
        })

    # ---- PIL decode check de todos los PNG/JPEG tallados ----
    from PIL import Image
    for e in report:
        if e["path"].endswith((".png", ".jpeg", ".jpg")):
            im = Image.open(repo / e["path"])
            im.load()
            e["pil_decode"] = "ok"
            e.setdefault("png_dims", list(im.size))

    report.sort(key=lambda r: r["path"])
    summary = {
        "total_files": len(report),
        "by_confidence": {},
        "naming_policy": "los pares de fuente se shipean como font_<width>/ porque el nombre real de carpeta no es recuperable por contenido (probes de path/proximidad descartados); ver docs/RECOVERY_LIMITS.md",
        "heap": {"file_offset": hex(HEAP_FILE_OFF), "size": hex(HEAP_SIZE)},
    }
    for r in report:
        summary["by_confidence"][r["confidence"]] = summary["by_confidence"].get(r["confidence"], 0) + 1
    (repo / "data" / "EXTRACTION_REPORT.json").write_text(
        json.dumps({"summary": summary, "files": report}, indent=1), encoding="utf-8")
    print(f"carved={len(report)} -> {out_root}")
    print("conf:", summary["by_confidence"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
