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
