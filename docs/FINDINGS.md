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

## Assets propios de Neon (138, espacio `assets/minecraft/client/`)

- GUI: `shader_v3/` (kawase blur, jump-flood outline, MTSDF, `skeet.frag`),
  fuentes (inter, museo, tahoma, stratum_2, sf_pro, skeet, eternal_ui,
  comic_sans, volte, epoca...), minimap, color picker.
- ESP: `esp/cop.png`, `esp/floyd.png` (skins), `images/esp_noise.png`.
- ML: `classifier/hotdog.dnet` (red neuronal embebida).
- Modelos 3D: `models/teapot.obj`, `models/penis.obj`, `models/arbuzica.obj`.
- Sonidos: `sounds/vine_boom.ogg`, `sounds/fortnut.wav`, `sounds/nut.wav`.
- Iconos/branding: `icons/neon_16/32.png`, `icons/jeffbenzos16/32.png`,
  `icons/stitch_16/32.png`, `images/logo.png`, `images/background.jpeg`.
- Otros: `images/Sayori_Hanging_s_kill.png`, `item_registries.json`,
  `subway/atlas.png` + `metadata.json`.

## Trazas de infraestructura (para el trabajo AOT abierto)

- `io.javalin` embebido: el cliente levanta un web server local — buscar
  rutas/config en constantes del heap es la vía más rápida para ver la
  superficie de control.
- zip4j 2.11.5: configs/themes cifradas con contraseña — el algoritmo será
  visible en el AOT cerca de las llamadas zip4j.
- Deep Netts: la red `hotdog.dnet` se carga desde recursos; la capa de
  inferencia está compilada en el AOT.
