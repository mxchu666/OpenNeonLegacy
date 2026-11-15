# Estructura del runtime extraído — imagen nativa GraalVM

## Veredicto principal

`neon_legacy.exe` NO contiene un jar ejecutable dentro del bundle: la
descompresión produce un ejecutable de **537,944,064 bytes** que es una
**imagen nativa de GraalVM** (SubstrateVM / native-image) del cliente completo.
Evidencia:

- 946 cadenas `com.oracle.svm` dentro del binario descomprimido.
- Sección `.svm_hea` de 411 MB (image heap) en el PE.
- `lib/font-runtime.txt` lo dice explícitamente:
  > The native libraries themselves are emitted beside the executable by GraalVM.

El belief inicial "GraalVM cifrado" era correcto a medias: ES GraalVM, y el
"cifrado" es el bundle NEONBND2 con zstd (sin criptografía real, solo
compresión).

## Secciones del PE (extracted/neon.exe)

| Sección   | vaddr      | tamaño     | rol                                    |
|-----------|-----------:|-----------:|----------------------------------------|
| .text     | 0x00001000 | 0x077BA000 | ~125 MB de código AOT (todo el cliente) |
| .rdata    | 0x077BB000 | 0x0000D000 | constantes                             |
| .data     | 0x077C8000 | 0x00003000 | datos                                  |
| .pdata    | 0x077CC000 | 0x00002000 | unwind                                 |
| .rodata   | 0x077CE000 | 0x0000A000 | rodata                                 |
| .svm_hea  | 0x077D8000 | 0x18823000 | **411 MB image heap**                  |
| .reloc    | 0x1FFFB000 | 0x0010C000 | reubicaciones                          |

El image heap guarda: todos los objetos inicializados (strings, arrays,
clases registradas), recursos embebidos como `byte[]` crudos, y metadatos.

## Identificación del contenido Java

- Clase principal: `net.minecraft.client.main.Main` (vanilla 1.8.9).
- `net/minecraft/client/ClientBrandRetriever`, `net/minecraft/realms/*`,
  `net/minecraft/server/MinecraftServer` presentes en el heap.
- El manifest firmado del jar original sobrevive en el heap
  (`Name: X.class` + `SHA-256-Digest` por entrada): se recuperaron las
  2,509 entradas (ver `data/JAR_ENTRIES.txt`).

## Librerías embebidas (inventario)

Java (nombres de módulo/manifest en el heap):

- imgui-java (`imgui.app`, `imgui.binding`, `imgui.lwjgl3`) — GUI
- **io.javalin** — web server embebido
- netty (módulos completos: codec/http2/dns/socks/proxy...)
- gson, guava, fastutil, jopt-simple, JNA
- **net.lingala.zip4j** — zips con contraseña (configs/themes)
- commons-codec, commons-io, commons-configuration(2), commons-lang
- org.json, jakarta annotation/transaction, javax.vecmath

C/C++ compiladas dentro del .text (símbolos mangled sobrevivientes):

- ImGui / ImPlot / ImGuizmo / rapidjson
- Assimp (modelos 3D: `teapot.obj`, `arbuzica.obj`, `penis.obj` en assets)
- Discord RPC
- openal-soft (jsound)
- stack-walker, ICU

## Assets propios de Neon (espacio `assets/minecraft/client/`)

138 recursos listados en `data/NEON_ASSETS.txt`: GUI shaders (kawase blur,
jump-flood outline, MTSDF, `skeet.frag`), fuentes (inter, museo, tahoma,
stratum, sf_pro, skeet, eternal_ui, comic_sans...), ESP skins (`cop.png`,
`floyd.png`), classifier ML (`hotdog.dnet`), modelos OBJ, sonidos
(`vine_boom.ogg`, `fortnut.wav`, `nut.wav`), e imágenes varias.

## Por qué no hay bytecode

La compilación AOT de native-image traduce cada método Java a x86-64 y
**descarta el bytecode**. No hay jar dentro (las firmas `PK\x01\x02`/`PK\x05\x06`
del binario son inmediatos del compilador en el código de `java.util.zip`
compilado, no zips reales). La recuperación del código Java verbatim es
imposible desde este artefacto; lo recuperable está en `RECOVERY_LIMITS.md`.
