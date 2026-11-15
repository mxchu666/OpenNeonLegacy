# OpenNeonLegacy

Ingeniería inversa completa del cliente **Neon Legacy** para Minecraft 1.8.9
(`neon_legacy.exe`, 268 MB) — del bundle hasta el runtime, con herramientas
reproducibles, mapas de deobfuscación y documentación del formato.

> Estado: análisis terminado sobre el artefacto completo. El trabajo de
> decompilación AOT (código máquina → Java legible) queda abierto y está
> documentado en `decompiled/`.

## Resumen de hallazgos

| Pregunta | Respuesta |
|---|---|
| ¿Qué es `neon_legacy.exe`? | Launcher MSVC (355 KB) + bundle `NEONBND2` (267.8 MB, zstd) |
| ¿Qué hay dentro del bundle? | 12 archivos: una **imagen nativa GraalVM** de 538 MB (el cliente completo) + DLLs de JVM/AWT |
| ¿Es GraalVM? | **Sí** — 946 cadenas `com.oracle.svm`, sección `.svm_hea` de 411 MB |
| ¿Hay un jar dentro? | **No.** El bytecode fue destruido por la compilación AOT |
| ¿Qué cliente es? | **Minecraft vanilla 1.8.9 exacto** (2,507 clases = el jar oficial de Mojang, clase a clase) + netty, con los mods de Neon **integrados dentro de clases vanilla** (re-obfuscación con el diccionario de vanilla) |
| ¿Qué librerías usa? | imgui-java + ImPlot/ImGuizmo/rapidjson/Assimp/Discord RPC (C), **Javalin**, netty, gson, guava, fastutil, zip4j, commons-* |
| ¿Se puede recuperar el código Java? | **No verbatim** (AOT lo destruye). Lo extraíble está completo en este repo; el resto requiere RE método a método — ver `docs/RECOVERY_LIMITS.md` |

## Estructura

```
tools/
  extract_bundle.ps1     extractor NEONBND2 (verificado 12/12, tamaños exactos)
  carve_named.py         talla recursos del image heap (headers SVM validados)
  carve_neon_assets.py   talla los 138 assets propios de Neon por path
  build_deobf_map.py     genera el mapa obf -> MCP (SRG 9.19)
data/
  BUNDLE_MANIFEST.csv    tabla de entradas del bundle con offsets
  JAR_ENTRIES.txt        2,509 clases del manifest firmado embebido
  DEOBF_CLASS_MAP.csv    2,507 clases mapeadas a nombres net.minecraft.*
  NEON_CLASS_DIFF.txt    diff exacto contra el client.jar oficial 1.8.9
  NEON_ASSETS.txt        138 recursos del espacio assets/minecraft/client/
docs/
  BUNDLE_FORMAT.md       especificación NEONBND2 (footer, tabla, zstd)
  RUNTIME_STRUCTURE.md   anatomía de la imagen nativa + inventario de libs
  RECOVERY_LIMITS.md     qué es y qué no es recuperable, y por qué
assets/                  recursos tallados del image heap
decompiled/              destino del trabajo AOT (aberto)
```

## Reproducir

```powershell
# 1. extraer el bundle
./tools/extract_bundle.ps1 -Bundle "D:\ruta\neon_legacy.exe" -OutDir extracted

# 2. mapa de deobfuscación (requiere mcp-1.8.9-srg.zip, md5 f5f8e81cd42f831d8d9979c0ffcb194e)
python tools/build_deobf_map.py mcp/extracted/joined.srg data/JAR_ENTRIES.txt data/DEOBF_CLASS_MAP.csv

# 3. tallar recursos del image heap (requiere el client.jar oficial 1.8.9 para nombres exactos)
python tools/carve_named.py extracted/neon.exe 0x77D7000 0x18823000 client.jar assets_out
```

## Reproducción de la base vanilla

La parte vanilla es pública y reconstruible con MCP-919 (decompilado) +
`data/DEOBF_CLASS_MAP.csv`, compilable con Gradle/Java 8. Las modificaciones
de Neon viven como diffs dentro de clases vanilla nombradas (`ave` = `Minecraft`,
`bcy` = `NetHandlerPlayClient`, etc.): identificarlas requiere comparar el AOT
contra el vanilla — el punto de partida está en `decompiled/`.

## Notas legales

- Este repo documenta análisis propio de un artefacto proporcionado por el
  propietario del estudio. No incluye el binario redistribuible.
- Los mapeos MCP son del ModCoderPack (dominio público de facto, CC BY-SA).
- Minecraft es de Mojang/Microsoft; la base vanilla no se redistribuye aquí.
