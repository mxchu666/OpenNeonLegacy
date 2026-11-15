# Trabajo AOT abierto — plan de decompilación

Este directorio recoge el resultado del trabajo de decompilación del código
AOT (`.text`, 125 MB) de `extracted/neon.exe`. Estado inicial: vacío.

## Punto de partida

- La imagen es una GraalVM native image: cada método Java es una función x86-64.
- Los nombres de clase están en `data/DEOBF_CLASS_MAP.csv` (obf → MCP).
- Los métodos concretos requieren identificarlos en el binario (no hay tabla
  de símbolos Java pública en la imagen; los strings `*_constructor_<sha>`
  y los descriptores sobrevivientes son las mejores anclas).
- Para trabajar: cargar `extracted/neon.exe` en IDA/Ghidra (538 MB, demo al
  índice inicial largo), usar el mapa de clases para navegar el heap
  (`.svm_hea` @ 0x77D8000) y localizar las constantes de cada clase.

## Orden de trabajo sugerido (por valor)

1. Clases tocadas por Neon con strings propias (auth/storage, raw input).
2. Javalin endpoints (web server embebido) — rutas HTTP legibles en el heap.
3. imgui GUI — labels/features en constantes del heap.
4. Resto de diffs vanilla detectados.

## Convención

Un archivo `.cpp`/`.java` por clase reconstruida, con el header:

```java
// Reconstrucción parcial desde AOT (neon.exe @ <offset>)
// Clase original: net.minecraft.client.<...> (obf: <obf_name>)
// Confianza: <alta|media|baja> — <notas>
```
