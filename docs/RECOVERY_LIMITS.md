# Límites de recuperación — qué es y qué no es posible

Este documento es la parte honesta del repo. `OpenNeonLegacy` **no** puede
devolver el código Java original del cliente, y esta es la razón técnica exacta.

## Qué se destruyó (irrecuperable desde este artefacto)

1. **El bytecode Java.** `native-image` compila cada método a x86-64 AOT y
   descarta el bytecode. El `.text` de 125 MB contiene métodos compilados, no
   clases. No existe ningún jar dentro del bundle (verificado: las firmas de
   zip en el binario son constantes de compilador).
2. **El árbol de llamadas Java legible.** La estructura de clases sigue
   presente (metadatos del heap) pero los cuerpos de los métodos solo existen
   como ensamblador optimizado, con inlining agresivo de Graal: el Java
   original ya no es reconstructible 1:1.

## Qué SÍ se recuperó (y está en este repo)

1. **Formato del bundle NEONBND2** completo, con extractor funcionando.
2. **Runtime completo extraído** (12 archivos, tamaños verificados).
3. **Inventario de clases completo** (2,509 entradas del manifest firmado).
4. **Identificación exacta del contenido**: cliente vanilla Minecraft 1.8.9
   (2,507 clases = el jar oficial de Mojang clase a clase) + netty, con las
   **modificaciones de Neon integradas dentro de clases vanilla** (0 clases
   añadidas con nombre distinto, 0 eliminadas — ver `data/NEON_CLASS_DIFF.txt`).
   Es decir: Neon re-obfuscó su build con el diccionario de vanilla.
5. **Mapa de deobfuscación** vanilla→MCP (mapeos MCP 9.19/1.8.9 oficiales,
   md5 verificado `f5f8e81c...`): cada clase `ave`/`bgx`/etc. tiene su nombre
   real `net.minecraft.*`.
6. **Inventario de librerías** Java y C++ embebidas.
7. **Recursos embebidos** (assets de Neon y de vanilla) tallados del image
   heap con validación de headers SVM.
8. **62 assets propios de Neon** en `assets/minecraft/client/` con reporte
   individual (`data/EXTRACTION_REPORT.json`: offset de heap, sha256,
   confianza, método). 40 high / 21 medium / 1 confirmed — la confianza
   "medium" significa que el nombre viene de un probe de contenido (dims
   exactas, keywords GLSL, matching espectral), no de un path.

## Assets propios: qué NO se recuperó (documentado, no simulado)

De las 138 rutas en `assets/minecraft/client/`, estas no tienen blob
recuperable en el heap — se documentan en vez de inventarse:

- `fonts/inter_medium.ttf` — no hay ningún TTF/OTF embebido; la fuente se
  resuelve en runtime (del sistema o remota).
- `icons/jeffbenzos16.png`, `images/arbuzica.png`, `images/circle.png`,
  `images/icons/cider.png`, `images/sliphack.png` — sin blob identificable.
- `models/penis.obj`, `models/arbuzica.obj` — solo `models/teapot.obj`
  está embebido (Utah teapot de NVIDIA, stats exactas: 3643 v / 6320 f).
- `sounds/fortnut.wav`, `sounds/nut.wav` — cero WAV en el heap.
- `item_registries.json` — no existe como JSON embebido; las referencias
  del heap son NBT vanilla.
- `subway/metadata.json` — el blob existe pero está corrupto en el heap
  (JSON inválido desde el char 82); no se publica un dump mangleado.
- Nombres reales de carpetas de fuentes: los 25 archivos de fuente se
  publican como `font_<width>/` (15 dirs). Las cadenas de path del heap no
  se pueden alinear con blobs por contenido (probes de proximidad/align
  descartados — ver hallazgos). La carpeta `font_2248` es la candidata a
  `fonts/skeet/` (2248², 2195 glyphs, lineH 1.0, kerning como lista) —
  hipótesis documentada, no verificable.
- 5 `metadata.json` de fuente (dirs font_1056/1088/1292/2224/2228)
  truncadas en el heap (colas de GC): la raíz de la de 2224 es visible en
  el heap pero no cierra.
- 81 blobs de texto GLSL sin mapeo a un path: inventario completo por
  sha256/tamaño/keywords en `data/SHADER_TEXT_BLOBS.json` (87 entradas,
  incluye las 6 publicadas). Solo se publican los 6 con keyword única.

## Cómo reconstruir algo buildeable

- La base vanilla 1.8.9 es reconstruible por cualquiera con MCP-919
  (decompilado completo) + los mapeos de este repo, y compilable con Gradle
  (Java 8). Es trabajo público y conocido, no contenido de este binario.
- Las modificaciones de Neon (dentro de clases vanilla) requieren RE del
  AOT: seleccionar método por método en IDA/Ghidra, con los nombres de clase
  como punto de partida. Es un trabajo de semanas, no un paso automático.
  El directorio `decompiled/` queda como destino de ese trabajo.

## Qué NO hace este repo

- No redistribuye el binario ni assets con copyright ajeno alineados a
  reventa. El análisis, la herramienta y los mapas son propios.
- No promete "100% del código fuente original": esa promesa sería falsa
  técnicamente. Lo que entrega es el 100% de lo que el formato permite
  extraer + el mapa para el resto.
