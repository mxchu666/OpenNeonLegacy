# Hallazgos del análisis — Neon Legacy

## Cadena de artefactos

```
neon_legacy.exe (268,134,046 B)
 ├── launcher MSVC C++ x64 (355 KB, 1,108 funciones, solo KERNEL32)
 └── bundle NEONBND2 (overlay @ 0x54400, 267.8 MB)
      └── 12 entradas zstd → imagen nativa GraalVM (538 MB) + DLLs JVM/AWT
           └── .text 125 MB (código AOT) + .svm_hea 411 MB (image heap)
                ├── 2,509 clases del jar original (manifest firmado en heap)
                ├── recursos embebidos como byte[] crudos
                └── constantes/strings del cliente
```

## Identificación del cliente

- Vanilla **1.8.9 exacto**: 2,507 clases coinciden 1:1 con el client.jar
  oficial de Mojang (diff: 0 añadidas con nombre distinto, 0 eliminadas,
  +2 marcadores de módulos de netty).
- Las modificaciones de Neon están **dentro de clases vanilla**: el build fue
  re-obfuscado con el diccionario de nombres de vanilla. Ejemplos de anclas:
  - `ave` = `net.minecraft.client.Minecraft`
  - `bcy` = `net.minecraft.client.network.NetHandlerPlayClient`
- Strings propias encontradas: `Unable to initialize neon_legacy storage`,
  `Neon native desktop checks`, `neonRawMouseInput`.

## Librerías embebidas (versiones donde visibles)

| Librería | Versión | Rol probable |
|---|---|---|
| netty-all | **4.1.89.Final** | red/protocolo |
| ViaVersion (com.viaversion) | — | multi-protocolo MC |
| Javalin + Jetty | — | web server embebido |
| imgui-java (+ ImPlot/ImGuizmo C) | — | GUI |
| rapidjson, Assimp, Discord RPC, openal-soft | — | C/C++ embebidas |
| Deep Netts (deepnetts-core) | — | **red neuronal** (`hotdog.dnet` classifier) |
| datafaker + generex | — | generación de datos falsos |
| okhttp / okhttp-urlconnection | — | HTTP client |
| zip4j | **2.11.5** | zips con contraseña (configs) |
| gson, guava, fastutil, joml, jopt-simple, jctools | — | utilidades |
| commons-codec/io/lang3/configuration2, org.json, snakeyaml | — | formatos |
| log4j-api/core, slf4j | — | logging |
| jlayer, codecjorbis (paulscode) | — | audio |
| oshi | — | info de OS |
| jcodings (jruby) | — | encodings |

## Assets propios de Neon (138 rutas en `assets/minecraft/client/`)

**62 archivos recuperados y publicados** en este repo (talla final con
`tools/carve_final.py`; reporte por archivo en `data/EXTRACTION_REPORT.json`).

Contenido y confianza:

| Grupo | Archivos | Confianza | Evidencia |
|---|---|---|---|
| Iconos (`icons/`) | 5 | 4 high, 1 medium | inspección visual (zoom sheets); jeffbenzos32 por eliminación |
| ESP (`esp/`) | 2 | high | inspección visual (cop = mugshot, floyd = retrato) |
| Imágenes (`images/`) | 17 PNG + 2 JPEG | mixta | visual; JPEGs por formato único + len-prefix SVM |
| Fuentes (`fonts/`) | blocky + 15 dirs `font_<W>/` (25 archivos) | high | pareo por dims exactas atlas↔metadata MTSDF (dist 22) |
| Shaders (6 de 87 blobs) | 6 GLSL | medium | keyword única (jfa, snow, stencil) + convención de uniforms MC |
| `classifier/hotdog.dnet` | 1 | confirmed | único blob dnet del heap, 5.3 MB Deep Netts |
| `models/teapot.obj` | 1 | confirmed | Utah teapot NVIDIA exacta: 3643 verts, 6320 caras |
| `sounds/vine_boom.ogg` | 1 | medium | matching espectral 0.9925 vs vine boom (3.265 s mono) |
| `subway/atlas.png` | 1 | medium | collage 4500×5000 visual |

Decisiones de publicación (importantes):

- **Nombres de fuentes**: `font_<width>/` — el nombre real de carpeta
  (inter, museo, tahoma, skeet...) no es recuperable por contenido; no se
  inventan nombres. La candidata a `skeet` es `font_2248` (hipótesis
  documentada en `RECOVERY_LIMITS.md`).
- **Shaders**: solo 6 blobs con keyword única se publican; los otros 81
  (incluyendo 8 vértices `u_mvp` idénticos entre sí) quedan inventariados
  por sha256/tamaño/keywords en `data/SHADER_TEXT_BLOBS.json`.
- `stars.frag` se escojió sobre su twin (2449 B): la publicada usa uniforms
  MC (`u_Sampler0`/`u_MaskSampler0`); el twin es el raw glslsandbox.
- Lo **no embebido** (penis.obj, fortnut.wav, item_registries.json,
  inter_medium.ttf, subway/metadata.json corrupta, jeffbenzos16, etc.)
  está listado y explicado en `docs/RECOVERY_LIMITS.md`.

## Trazas de infraestructura (para el trabajo AOT abierto)

- `io.javalin` embebido: el cliente levanta un web server local — buscar
  rutas/config en constantes del heap es la vía más rápida para ver la
  superficie de control.
- zip4j 2.11.5: configs/themes cifradas con contraseña — el algoritmo será
  visible en el AOT cerca de las llamadas zip4j.
- Deep Netts: la red `hotdog.dnet` se carga desde recursos; la capa de
  inferencia está compilada en el AOT.
